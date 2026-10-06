/* SPDX-License-Identifier: GPL-2.0-only
 * Post-TDM CPU power saving, model-specific fan minima and telemetry.
 * No GPU driver, no manual fan mode, no disk mounts.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static const char *root = "";
static void path_for(char *path, size_t size, const char *relative) {
    if (snprintf(path, size, "%s%s", root, relative) >= (int)size) {
        fprintf(stderr, "health: path too long\n"); exit(1);
    }
}
static bool read_value(const char *path, char *value, size_t size) {
    FILE *file = fopen(path, "r");
    if (!file) return false;
    bool ok = fgets(value, (int)size, file) != NULL;
    fclose(file);
    if (ok) value[strcspn(value, "\r\n")] = 0;
    return ok;
}
static bool has_word(const char *list, const char *word) {
    size_t n = strlen(word);
    const char *p = list;
    while ((p = strstr(p, word))) {
        if ((p == list || p[-1] == ' ') && (!p[n] || p[n] == ' ')) return true;
        p += n;
    }
    return false;
}
static void load_module(const char *name) {
    char path[256];
    snprintf(path, sizeof path, "/modules/%s.ko", name);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) { printf("health: module %s unavailable\n", name); return; }
    int result = (int)syscall(SYS_finit_module, fd, "", 0);
    int saved = errno;
    close(fd);
    if (result && saved != EEXIST)
        printf("health: %s not active: %s (may be unsupported on this CPU)\n", name, strerror(saved));
    else printf("health: %s loaded\n", name);
}
static void configure_cpu(void) {
    char base[1024];
    path_for(base, sizeof base, "/sys/devices/system/cpu/cpufreq");
    DIR *dir = opendir(base);
    if (!dir) { puts("health: no CPU frequency policies available"); return; }
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (strncmp(entry->d_name, "policy", 6)) continue;
        char path[1400], governors[512], driver[128];
        snprintf(path, sizeof path, "%s/%s/scaling_driver", base, entry->d_name);
        if (!read_value(path, driver, sizeof driver)) continue;
        /* Only known Intel/ACPI drivers; leave unknown policy implementations alone. */
        if (strcmp(driver, "acpi-cpufreq") && strcmp(driver, "intel_pstate") && strcmp(driver, "intel_cpufreq")) continue;
        snprintf(path, sizeof path, "%s/%s/scaling_available_governors", base, entry->d_name);
        if (!read_value(path, governors, sizeof governors) || !has_word(governors, "powersave")) {
            printf("health: %s has no powersave governor; unchanged\n", entry->d_name); continue;
        }
        snprintf(path, sizeof path, "%s/%s/scaling_governor", base, entry->d_name);
        FILE *file = fopen(path, "w");
        if (!file) { printf("health: cannot change %s governor\n", entry->d_name); continue; }
        bool ok = fputs("powersave\n", file) >= 0;
        if (fclose(file)) ok = false;
        printf("health: %s powersave %s\n", entry->d_name, ok ? "requested" : "failed");
    }
    closedir(dir);
}

static bool cooling_configured;
static bool read_relative(const char *relative, char *value, size_t size) {
    char path[1400]; path_for(path,sizeof path,relative);
    return read_value(path,value,size);
}
static bool read_number(const char *relative, long *number) {
    char value[64], *end;
    if (!read_relative(relative,value,sizeof value)) return false;
    errno=0; *number=strtol(value,&end,10);
    return !errno && end!=value && !*end && *number>=0;
}
static void configure_fans(void) {
    char value[1024], relative[256];
    if (!read_relative("/sys/class/dmi/id/product_name",value,sizeof value) || strcmp(value,"iMac11,1")) return;
    if (!read_relative("/sys/class/dmi/id/board_name",value,sizeof value) || strcmp(value,"Mac-F2268DAE")) return;
    if (read_relative("/proc/cmdline",value,sizeof value) && has_word(value,"tdm.fans=0")) {
        puts("health: increased cooling disabled by boot option"); return;
    }
    const char *labels[]={"ODD","HDD","CPU"};
    const long targets[]={1800,1800,1500};
    long previous[3];
    /* Validate every fan before changing anything. Never lower an existing minimum. */
    for(int i=0;i<3;i++) {
        long manual,max;
        snprintf(relative,sizeof relative,"/sys/devices/platform/applesmc.768/fan%d_label",i+1);
        if (!read_relative(relative,value,sizeof value)) return;
        value[strcspn(value," \t")]=0;
        if (strcmp(value,labels[i])) return;
        snprintf(relative,sizeof relative,"/sys/devices/platform/applesmc.768/fan%d_manual",i+1);
        if (!read_number(relative,&manual) || manual!=0) return;
        snprintf(relative,sizeof relative,"/sys/devices/platform/applesmc.768/fan%d_max",i+1);
        if (!read_number(relative,&max) || max<targets[i]) return;
        snprintf(relative,sizeof relative,"/sys/devices/platform/applesmc.768/fan%d_min",i+1);
        if (!read_number(relative,&previous[i]) || previous[i]>max) return;
    }
    cooling_configured=true;
    for(int i=0;i<3;i++) {
        char path[1400]; long actual;
        if (previous[i]>=targets[i]) continue;
        snprintf(relative,sizeof relative,"/sys/devices/platform/applesmc.768/fan%d_min",i+1);
        path_for(path,sizeof path,relative);
        FILE *f=fopen(path,"w");
        bool ok=false;
        if (f) { ok=fprintf(f,"%ld\n",targets[i])>0; if(fclose(f))ok=false; }
        if (!ok || !read_number(relative,&actual) || actual<targets[i]) {
            cooling_configured=false; printf("health: %s minimum write/readback failed\n",labels[i]);
        } else printf("health: %s minimum %ld RPM; automatic control preserved\n",labels[i],actual);
    }
}

static bool sensor_attribute(const char *name) {
    const char *p;
    bool fan = !strncmp(name, "fan", 3);
    if (fan) p = name + 3;
    else if (!strncmp(name, "temp", 4)) p = name + 4;
    else return false;
    if (*p < '0' || *p > '9') return false;
    while (*p >= '0' && *p <= '9') p++;
    return !strcmp(p,"_input") || !strcmp(p,"_label") || !strcmp(p,"_crit") ||
           !strcmp(p,"_max") || !strcmp(p,"_alarm") || !strcmp(p,"_fault") ||
           (fan && (!strcmp(p,"_min") || !strcmp(p,"_manual")));
}
static int list_sensors(FILE *out, const char *path) {
    DIR *dir = opendir(path);
    if (!dir) return 0;
    int count = 0;
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (!sensor_attribute(entry->d_name)) continue;
        char file[2048], value[256];
        if (snprintf(file,sizeof file,"%s/%s",path,entry->d_name) >= (int)sizeof file) continue;
        if (read_value(file,value,sizeof value)) { fprintf(out,"  %s=%s\n",entry->d_name,value); count++; }
    }
    closedir(dir);
    return count;
}
static void snapshot(FILE *out) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    fprintf(out,"TDM health at %ld s: temperatures in millidegrees C; fans in RPM\n",now.tv_sec);
    char base[1024];
    path_for(base,sizeof base,"/sys/devices/system/cpu/cpufreq");
    DIR *dir = opendir(base);
    int policies = 0, sensors = 0;
    struct dirent *entry;
    if (dir) {
        while ((entry = readdir(dir))) {
            if (strncmp(entry->d_name,"policy",6)) continue;
            const char *fields[] = {"scaling_driver","scaling_governor","scaling_cur_freq","scaling_min_freq","scaling_max_freq"};
            fprintf(out,"CPU %s (frequencies in kHz)\n",entry->d_name); policies++;
            for (size_t i=0;i<sizeof fields/sizeof fields[0];i++) {
                char path[1400],value[256];
                snprintf(path,sizeof path,"%s/%s/%s",base,entry->d_name,fields[i]);
                if (read_value(path,value,sizeof value)) fprintf(out,"  %s=%s\n",fields[i],value);
            }
        }
        closedir(dir);
    }
    if (!policies) fputs("CPU frequency scaling unavailable; idle states are separate\n",out);
    path_for(base,sizeof base,"/sys/class/hwmon");
    dir = opendir(base);
    if (dir) {
        while ((entry = readdir(dir))) {
            if (strncmp(entry->d_name,"hwmon",5)) continue;
            char path[1400],namepath[1500],name[256]="unknown";
            snprintf(path,sizeof path,"%s/%s",base,entry->d_name);
            snprintf(namepath,sizeof namepath,"%s/name",path);
            if (!read_value(namepath,name,sizeof name)) {
                snprintf(namepath,sizeof namepath,"%s/device/name",path);
                read_value(namepath,name,sizeof name);
            }
            fprintf(out,"Sensors %s (%s)\n",entry->d_name,name);
            sensors += list_sensors(out,path);
            /* Legacy applesmc exports its attributes on the parent platform device. */
            snprintf(path,sizeof path,"%s/%s/device",base,entry->d_name);
            sensors += list_sensors(out,path);
        }
        closedir(dir);
    }
    if (!sensors) fputs("Temperature/fan readings unavailable; cooling is NOT verified\n",out);
    fputs(cooling_configured ? "Increased fan minima active; automatic SMC control; no GPU modules loaded\n" : "Fan profile not applied or incomplete; inspect fan telemetry; no GPU modules loaded\n",out);
    fflush(out);
}
int main(int argc, char **argv) {
    if (argc == 3 && !strcmp(argv[1],"--fixture")) {
        root=argv[2]; configure_cpu(); configure_fans(); snapshot(stdout); return 0;
    }
    bool diagnostic = argc == 2 && !strcmp(argv[1],"--diagnostics");
    bool test = argc == 2 && !strcmp(argv[1],"--test");
    if (argc > 2 || (argc == 2 && !diagnostic && !test)) return 2;
    struct utsname u;
    if (uname(&u) || strcmp(u.release,"6.6.8-tinycore64")) {
        fprintf(stderr,"health: kernel mismatch, refusing module loads\n"); return 1;
    }
    puts("health: post-TDM CPU and sensor setup starting"); fflush(stdout);
    load_module("acpi-cpufreq");
    load_module("cpufreq_powersave");
    load_module("coretemp");
    /* Never access SMC in the VM test mode. In production TDM has finished first. */
    if (!test) load_module("applesmc");
    configure_cpu();
    if (!test) configure_fans();
    mkdir("/run",0700);
    for (;;) {
        while (waitpid(-1,NULL,WNOHANG)>0) {}
        if (diagnostic) fputs("\033[2J\033[H",stdout);
        snapshot(stdout);
        FILE *out=fopen("/run/health.new","w");
        if (out) {
            snapshot(out);
            if (!fclose(out)) rename("/run/health.new","/run/health.txt");
        }
        struct timespec delay={.tv_sec=15};
        while (nanosleep(&delay,&delay) && errno==EINTR) {}
    }
}
