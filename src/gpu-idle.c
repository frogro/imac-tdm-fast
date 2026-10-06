/* Tested RV770 link cycle. Not a power-off: restores link after 30 seconds. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdlib.h>
#include <signal.h>
#include <string.h>
#include <time.h>
static int bridge=-1,ep[2]={-1,-1},changed=0,failed=0; static unsigned ctl; static unsigned char original[2][256]; static volatile sig_atomic_t stop;
static void nap(int ms){struct timespec t={ms/1000,ms%1000*1000000};nanosleep(&t,0);}
static unsigned readreg(int f,int o,int n){unsigned v=0;if(pread(f,&v,n,o)!=n){perror("readreg");return ~0u;}return v;}
static int writereg(int f,int o,unsigned v,int n){if(pwrite(f,&v,n,o)!=n){perror("writereg");failed=1;return -1;}return 0;}
static unsigned saved(int e,int o,int n){unsigned v=0;memcpy(&v,original[e]+o,n);return v;}
static void sig(int s){(void)s;stop=1;}
static void restore(void){
 if(!changed)return;
 changed=0;
 puts("RESTORING LINK");writereg(bridge,0xa0,ctl,2);
 for(int i=0;i<200;i++){nap(10);if(readreg(ep[0],0,4)==0x944a1002)break;}
 for(int e=0;e<2;e++){
  if(readreg(ep[e],0,4)!=saved(e,0,4)){printf("RESTORE FAILED endpoint %d unreachable; power cycle may be needed\n",e);failed=1;continue;}
  writereg(ep[e],4,readreg(ep[e],4,2)&~7,2);
  for(int o=0x10;o<=0x24;o+=4)if(readreg(ep[e],o,4)!=saved(e,o,4))writereg(ep[e],o,saved(e,o,4),4);
  if(readreg(ep[e],0x30,4)!=saved(e,0x30,4))writereg(ep[e],0x30,saved(e,0x30,4),4);
  writereg(ep[e],0x0c,saved(e,0x0c,1),1);
  writereg(ep[e],0x3c,saved(e,0x3c,1),1);
  writereg(ep[e],0x60,saved(e,0x60,2),2);
  writereg(ep[e],0x68,saved(e,0x68,2),2);
  writereg(ep[e],4,saved(e,4,2),2);
  for(int o=0;o<256;o++)if(readreg(ep[e],o,1)!=original[e][o])printf("CONFIG_DIFF ep=%d offset=%02x before=%02x after=%02x\n",e,o,original[e][o],readreg(ep[e],o,1));
 }
 printf("RESTORED LinkCtl=%04x LinkSta=%04x\n",readreg(bridge,0xa0,2),readreg(bridge,0xa2,2));
}
static int matches(const char *path, const char *expected) {
 char b[100]; FILE *f=fopen(path,"r"); if(!f)return 0;
 int ok=fgets(b,sizeof b,f)!=NULL; fclose(f);
 if(!ok)return 0;
 b[strcspn(b,"\n")]=0; return !strcmp(b,expected);
}
int main(int argc,char **argv){
 setvbuf(stdout,0,_IOLBF,0);
 if(!matches("/sys/class/dmi/id/product_name","iMac11,1") ||
    !matches("/sys/class/dmi/id/board_name","Mac-F2268DAE")) {
  puts("SKIP: GPU workaround is restricted to tested iMac11,1 board"); return 0;
 }
 for(int e=0;e<2;e++){
  char p[128];snprintf(p,sizeof p,"/sys/bus/pci/devices/0000:01:00.%d/driver",e);
  if(access(p,F_OK)==0){puts("REFUSE: endpoint driver bound");return 1;}
  snprintf(p,sizeof p,"/sys/bus/pci/devices/0000:01:00.%d/config",e);ep[e]=open(p,O_RDWR);
  if(ep[e]<0||pread(ep[e],original[e],256,0)!=256)return 1;
 }
 if(saved(0,0,4)!=0x944a1002||saved(1,0,4)!=0xaa301002)return 1;
 bridge=open("/sys/bus/pci/devices/0000:00:03.0/config",O_RDWR);
 if(bridge<0||readreg(bridge,0,4)!=0xd1388086||readreg(bridge,0x90,1)!=0x10||((readreg(bridge,0x92,2)>>4)&15)!=4)return 1;
 ctl=readreg(bridge,0xa0,2);if(ctl&0x30){puts("REFUSE: link disabled or retraining");return 1;}
 printf("PREFLIGHT LinkCtl=%04x LinkSta=%04x\n",ctl,readreg(bridge,0xa2,2));
 if(argc!=2||strcmp(argv[1],"--apply"))return 0;
 atexit(restore);signal(SIGTERM,sig);signal(SIGINT,sig);signal(SIGHUP,sig);
 changed=1;
 for(int e=0;e<2;e++)if(writereg(ep[e],4,saved(e,4,2)&~7,2))return 1;
 if(writereg(bridge,0xa0,ctl|0x10,2))return 1;
 for(int i=0;i<30&&!stop;i++){
  nap(1000);
  FILE *f=fopen("/sys/class/hwmon/hwmon1/device/temp10_input","r");int t=0;
  if(!f||fscanf(f,"%d",&t)!=1){if(f)fclose(f);puts("ABORT sensor unavailable");break;}fclose(f);
  printf("LINK_DISABLED seconds=%d ctl=%04x status=%04x temp=%d\n",i+1,readreg(bridge,0xa0,2),readreg(bridge,0xa2,2),t);
  if(t>=90000){puts("ABORT temperature ceiling");break;}
 }
 restore();return failed?1:0;
}
