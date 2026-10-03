/* SPDX-License-Identifier: GPL-2.0-only
 * Minimal PID 1: start TDM and handle the physical power button, entirely in RAM.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/fb.h>
#include <stdint.h>
#include <sys/mman.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define MAX_INPUTS 32
static struct pollfd inputs[MAX_INPUTS];
static char paths[MAX_INPUTS][256];
static bool armed[MAX_INPUTS];
static int input_count;

static void logmsg(const char *message) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    printf("[tdm-fast %ld.%03ld] %s\n", t.tv_sec, t.tv_nsec / 1000000, message);
    fflush(stdout);
}
static bool read_text(const char *path, char *buffer, size_t size) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return false;
    ssize_t n = read(fd, buffer, size - 1);
    close(fd);
    if (n < 0) return false;
    buffer[n] = 0;
    buffer[strcspn(buffer, "\r\n")] = 0;
    return true;
}
/* Optional splash, never a prerequisite for TDM or the power button. */
static void draw_splash(void) {
    char numbers[64];
    unsigned int major_num, minor_num;
    if (!read_text("/sys/class/graphics/fb0/dev", numbers, sizeof numbers) ||
        sscanf(numbers, "%u:%u", &major_num, &minor_num) != 2) return;
    if (mknod("/dev/fb0", S_IFCHR | 0600, makedev(major_num, minor_num)) && errno != EEXIST) return;
    int fd = open("/dev/fb0", O_RDWR | O_CLOEXEC);
    if (fd < 0) return;
    struct fb_fix_screeninfo f;
    struct fb_var_screeninfo v;
    if (ioctl(fd, FBIOGET_FSCREENINFO, &f) || ioctl(fd, FBIOGET_VSCREENINFO, &v)) {
        close(fd); return;
    }
    unsigned int bytes = v.bits_per_pixel / 8;
    if (f.type != FB_TYPE_PACKED_PIXELS || f.visual != FB_VISUAL_TRUECOLOR ||
        (v.bits_per_pixel != 16 && v.bits_per_pixel != 24 && v.bits_per_pixel != 32) ||
        v.xres < 180 || v.yres < 180 || v.xres > 16384 || v.yres > 16384 ||
        v.red.length > 8 || v.green.length > 8 || v.blue.length > 8 ||
        v.red.offset + v.red.length > v.bits_per_pixel ||
        v.green.offset + v.green.length > v.bits_per_pixel ||
        v.blue.offset + v.blue.length > v.bits_per_pixel ||
        (uint64_t)(v.xoffset + v.xres) * bytes > f.line_length ||
        (uint64_t)(v.yoffset + v.yres) * f.line_length > f.smem_len ||
        f.smem_len > 256U * 1024 * 1024) { close(fd); return; }
    unsigned char pixels[180 * 180];
    int logo = open("/splash.gray", O_RDONLY | O_CLOEXEC);
    if (logo < 0) { close(fd); return; }
    size_t got = 0;
    while (got < sizeof pixels) {
        ssize_t n = read(logo, pixels + got, sizeof pixels - got);
        if (n <= 0) break;
        got += (size_t)n;
    }
    close(logo);
    if (got != sizeof pixels) { close(fd); return; }
    unsigned char *fb = mmap(NULL, f.smem_len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (fb == MAP_FAILED) { close(fd); return; }
    for (unsigned int y = 0; y < v.yres; y++)
        memset(fb + (size_t)(v.yoffset + y) * f.line_length + v.xoffset * bytes, 0, v.xres * bytes);
    for (unsigned int y = 0; y < 180; y++) for (unsigned int x = 0; x < 180; x++) {
        unsigned int g = pixels[y * 180 + x];
        uint32_t color = ((g * ((1U << v.red.length) - 1) / 255) << v.red.offset) |
                         ((g * ((1U << v.green.length) - 1) / 255) << v.green.offset) |
                         ((g * ((1U << v.blue.length) - 1) / 255) << v.blue.offset);
        size_t offset = (size_t)(v.yoffset + (v.yres - 180) / 2 + y) * f.line_length +
                       (v.xoffset + (v.xres - 180) / 2 + x) * bytes;
        memcpy(fb + offset, &color, bytes);
    }
    munmap(fb, f.smem_len); close(fd);
    logmsg("Static splash drawn");
}
static bool boot_flag(const char *text, const char *flag) {
    size_t length = strlen(flag);
    const char *p = text;
    while ((p = strstr(p, flag))) {
        if ((p == text || p[-1] == ' ') &&
            (p[length] == 0 || p[length] == ' ' || p[length] == '\n')) return true;
        p += length;
    }
    return false;
}
static int smc(const char *key, const char *value) {
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (pid == 0) {
        execl("/smc", "smc", key, value, (char *)NULL);
        _exit(127);
    }
    int status;
    while (waitpid(pid, &status, 0) < 0) if (errno != EINTR) return -1;
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}
static int start_tdm(bool test) {
    if (test) {
        logmsg("TEST: SMC hardware access disabled");
        return 0;
    }
    char vendor[128] = "", model[128] = "";
    read_text("/sys/class/dmi/id/sys_vendor", vendor, sizeof vendor);
    read_text("/sys/class/dmi/id/product_name", model, sizeof model);
    if (!strstr(vendor, "Apple") ||
        (strcmp(model, "iMac10,1") && strcmp(model, "iMac11,1"))) {
        logmsg("Unsupported hardware: this build targets the late-2009 27-inch iMac. No SMC writes.");
        return 1;
    }
    logmsg("TDM: writing MVHR=1");
    if (smc("MVHR", "1")) {
        logmsg("ERROR: MVHR failed; TDM not confirmed");
        return 1;
    }
    /* Keep the original working stick's hardware settling time. No boot delay. */
    struct timespec delay = {.tv_sec = 1};
    while (nanosleep(&delay, &delay) && errno == EINTR) {}
    logmsg("TDM: writing MVMR=2");
    if (smc("MVMR", "2")) {
        logmsg("ERROR: MVMR failed; TDM not confirmed");
        return 1;
    }
    logmsg("TDM commands accepted; physical display state is not measured");
    return 0;
}
static bool bit(const unsigned char *bits, unsigned int key) {
    return (bits[key / 8] & (1U << (key % 8))) != 0;
}
static void discover_inputs(void) {
    DIR *dir = opendir("/sys/class/input");
    if (!dir) return;
    struct dirent *entry;
    while ((entry = readdir(dir)) && input_count < MAX_INPUTS) {
        if (strncmp(entry->d_name, "event", 5)) continue;
        char path[256];
        if (snprintf(path, sizeof path, "/dev/input/%s", entry->d_name) >= (int)sizeof path) continue;
        bool known = false;
        for (int i = 0; i < input_count; i++) if (!strcmp(paths[i], path)) known = true;
        if (known) continue;
        char sysdev[320], numbers[64];
        unsigned int major_num, minor_num;
        snprintf(sysdev, sizeof sysdev, "/sys/class/input/%s/dev", entry->d_name);
        if (!read_text(sysdev, numbers, sizeof numbers) ||
            sscanf(numbers, "%u:%u", &major_num, &minor_num) != 2) continue;
        if (mknod(path, S_IFCHR | 0600, makedev(major_num, minor_num)) && errno != EEXIST) continue;
        int fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) continue;
        unsigned char keys[(KEY_MAX + 8) / 8] = {0};
        if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof keys), keys) < 0 || !bit(keys, KEY_POWER)) {
            close(fd);
            continue;
        }
        unsigned char pressed[sizeof keys] = {0};
        if (ioctl(fd, EVIOCGKEY(sizeof pressed), pressed) < 0) { close(fd); continue; }
        armed[input_count] = !bit(pressed, KEY_POWER);
        strcpy(paths[input_count], path);
        inputs[input_count++] = (struct pollfd){.fd = fd, .events = POLLIN};
        logmsg("Power button ready");
    }
    closedir(dir);
}
static void poweroff(void) {
    logmsg("Power button: immediate poweroff (RAM-only, no disks mounted)");
    /* No block filesystems, no persistent writes, no shutdown services. */
    reboot(RB_POWER_OFF);
    logmsg("ERROR: firmware poweroff failed; hold the physical power button");
}
int main(void) {
    if (getpid() != 1) { fprintf(stderr, "Must run as PID 1\n"); return 1; }
    mkdir("/dev", 0755); mkdir("/proc", 0555); mkdir("/sys", 0555);
    /* TinyCore's kernel may lack devtmpfs: create input nodes from sysfs below. */
    if (mount("devtmpfs", "/dev", "devtmpfs", MS_NOSUID, "mode=0755") && errno != EBUSY)
        logmsg("Using minimal static /dev with sysfs input discovery");
    mkdir("/dev/input", 0755);
    if (mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL))
        logmsg("ERROR: proc mount failed");
    if (mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL))
        logmsg("ERROR: sysfs mount failed");
    char cmdline[4096] = "";
    read_text("/proc/cmdline", cmdline, sizeof cmdline);
    bool test = boot_flag(cmdline, "tdm.test=1");
    bool diagnostic = boot_flag(cmdline, "tdm.diagnostics=1");
    if (!diagnostic) draw_splash();
    logmsg("Minimal RAM system started");
    pid_t worker = fork();
    if (worker == 0) {
        if (diagnostic) logmsg("DIAGNOSTICS: display stays internal; TDM commands skipped");
        else if (start_tdm(test)) logmsg("TDM startup failed; continuing with CPU/sensor setup");
        /* SMC direct-I/O helper has exited before applesmc can claim its ports. */
        if (test) execl("/health", "health", "--test", (char *)NULL);
        else if (diagnostic) execl("/health", "health", "--diagnostics", (char *)NULL);
        else execl("/health", "health", (char *)NULL);
        logmsg("ERROR: cannot start CPU/thermal monitor");
        _exit(1);
    }
    if (worker < 0) logmsg("ERROR: cannot start TDM worker");
    for (;;) {
        discover_inputs();
        int status;
        pid_t child;
        while ((child = waitpid(-1, &status, WNOHANG)) > 0) {
            if (child == worker && (!WIFEXITED(status) || WEXITSTATUS(status)))
                logmsg("TDM/health worker exited; power button remains available");
        }
        if (poll(inputs, (nfds_t)input_count, 1000) <= 0) continue;
        for (int i = 0; i < input_count; i++) {
            if (inputs[i].revents & POLLIN) {
                struct input_event ev;
                while (read(inputs[i].fd, &ev, sizeof ev) == sizeof ev) {
                    if (ev.type != EV_KEY || ev.code != KEY_POWER) continue;
                    if (ev.value == 0) armed[i] = true;
                    if (ev.value == 1 && armed[i]) poweroff();
                }
            }
            if (inputs[i].revents & (POLLHUP | POLLERR | POLLNVAL)) {
                close(inputs[i].fd);
                int last = --input_count;
                inputs[i] = inputs[last]; armed[i] = armed[last];
                memmove(paths[i], paths[last], sizeof paths[i]); i--;
            }
        }
    }
}
