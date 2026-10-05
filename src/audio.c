/* SPDX-License-Identifier: GPL-2.0-only
 * Experimental speaker initialization, not a verified DisplayPort audio route.
 * No GPU modules, codec verbs, raw SMC writes, or persistent disk access.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <sound/asound.h>

static int readtext(const char *path, char *buf, size_t size) {
    FILE *f=fopen(path,"r"); if (!f) return 0;
    int ok=fgets(buf,(int)size,f)!=NULL; fclose(f);
    if (ok) buf[strcspn(buf,"\r\n")]=0;
    return ok;
}
static void module(const char *name) {
    char path[256]; snprintf(path,sizeof path,"/modules/%s.ko",name);
    int fd=open(path,O_RDONLY|O_CLOEXEC);
    if(fd<0) {printf("audio: missing %s\n",name);return;}
    const char *args=!strcmp(name,"snd-hda-intel") ? "power_save=0" : "";
    int rc=(int)syscall(SYS_finit_module,fd,args,0), err=errno; close(fd);
    printf("audio: %s: %s\n",name,rc && err!=EEXIST ? strerror(err):"loaded");
}
static void mixer(int card) {
    char path[256],buf[128]; unsigned major_num,minor_num;
    snprintf(path,sizeof path,"/sys/class/sound/controlC%d/dev",card);
    if(!readtext(path,buf,sizeof buf) || sscanf(buf,"%u:%u",&major_num,&minor_num)!=2) return;
    snprintf(path,sizeof path,"/dev/snd/controlC%d",card);
    if(mknod(path,S_IFCHR|0600,makedev(major_num,minor_num)) && errno!=EEXIST) return;
    int fd=open(path,O_RDWR|O_CLOEXEC); if(fd<0)return;
    struct snd_ctl_card_info ci={0};
    if(!ioctl(fd,SNDRV_CTL_IOCTL_CARD_INFO,&ci)) printf("audio: card %d %s\n",card,ci.longname);
    struct snd_ctl_elem_list list={0};
    if(ioctl(fd,SNDRV_CTL_IOCTL_ELEM_LIST,&list) || list.count>4096) {close(fd);return;}
    list.space=list.count;list.pids=calloc(list.space,sizeof *list.pids);
    if(!list.pids || ioctl(fd,SNDRV_CTL_IOCTL_ELEM_LIST,&list)) {free(list.pids);close(fd);return;}
    for(unsigned i=0;i<list.used;i++) {
        struct snd_ctl_elem_info info={0};info.id=list.pids[i];
        if(ioctl(fd,SNDRV_CTL_IOCTL_ELEM_INFO,&info))continue;
        const char *name=(const char *)info.id.name;
        printf("audio: control %s type=%d count=%u\n",name,info.type,info.count);
        if(info.id.iface!=SNDRV_CTL_ELEM_IFACE_MIXER || !(info.access&SNDRV_CTL_ELEM_ACCESS_WRITE) || info.count>128)continue;
        int sw=!strcmp(name,"Master Playback Switch") || !strcmp(name,"Speaker Playback Switch");
        int vol=!strcmp(name,"Master Playback Volume") || !strcmp(name,"Speaker Playback Volume") || !strcmp(name,"PCM Playback Volume");
        if(!((sw && info.type==SNDRV_CTL_ELEM_TYPE_BOOLEAN) || (vol && info.type==SNDRV_CTL_ELEM_TYPE_INTEGER)))continue;
        struct snd_ctl_elem_value value={0};value.id=info.id;
        if(ioctl(fd,SNDRV_CTL_IOCTL_ELEM_READ,&value))continue;
        long target=1;
        if(vol) {
            long min=info.value.integer.min,max=info.value.integer.max,step=info.value.integer.step;
            if(max<min || min<0 || max>1000000)continue;
            target=min+(max-min)*40/100;
            if(step>0)target=min+((target-min)/step)*step;
        }
        for(unsigned j=0;j<info.count;j++)value.value.integer.value[j]=target;
        printf("audio: set %s=%ld: %s\n",name,target,ioctl(fd,SNDRV_CTL_IOCTL_ELEM_WRITE,&value)?strerror(errno):"OK");
    }
    free(list.pids);close(fd);
}
int main(int argc,char **argv) {
    int test=argc==2 && !strcmp(argv[1],"--test");
    if(argc>2 || (argc==2 && !test))return 2;
    struct utsname u;char vendor[128],model[128];
    if(uname(&u) || strcmp(u.release,"6.6.8-tinycore64"))return 1;
    if(!test && (!readtext("/sys/class/dmi/id/sys_vendor",vendor,sizeof vendor) ||
        !readtext("/sys/class/dmi/id/product_name",model,sizeof model) || !strstr(vendor,"Apple") ||
        (strcmp(model,"iMac10,1") && strcmp(model,"iMac11,1"))))return 1;
    mkdir("/run",0700);mkdir("/dev/snd",0755);
    int serial=test ? dup(STDOUT_FILENO) : -1;
    FILE *log=fopen("/run/audio.txt","w");
    if(log){fflush(stdout);dup2(fileno(log),STDOUT_FILENO);fclose(log);}
    setvbuf(stdout,NULL,_IOLBF,0);
    puts("audio: experimental HDA speaker setup; DisplayPort audio not verified");
    const char *mods[]={"soundcore","snd","snd-timer","snd-pcm","snd-hwdep",
        "snd-hda-core","snd-hda-codec","snd-hda-codec-generic","snd-hda-codec-cirrus",
        "snd-hda-codec-realtek","snd-intel-dspcfg","snd-hda-intel"};
    for(unsigned i=0;i<sizeof mods/sizeof mods[0];i++)module(mods[i]);
    /* HDA codec probing may run asynchronously. */
    sleep(2);
    for(int card=0;card<8;card++)mixer(card);
    puts("audio: setup finished; no GPU modules or disk writes");
    if(serial>=0) {
        FILE *f=fopen("/run/audio.txt","r"); char line[512];
        if(f){while(fgets(line,sizeof line,f))dprintf(serial,"%s",line);fclose(f);}
        close(serial);
    }
    return 0;
}
