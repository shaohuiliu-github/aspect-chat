/* Re-evaluate original I2VIS material routines after calibrated marker T edits.
 * No timestep, velocity solve, or transport step is performed. */
#define main chatgfd_upstream_initializer_main
#include <in2fasth5.c>
#undef main
int main(void){
 loadconf();loader(0,0);
 for(int pass=0;pass<2;pass++){
  ronurecalc();
  if(GYKOEF>0)for(long m1=1;m1<xnumx;m1++){
   long m3=m1*ynumy+1;pr[m3]=pinit;
   for(long m2=2;m2<ynumy;m2++){m3++;pr[m3]=pr[m3-1]+(gy[m2]-gy[m2-2])/2.0*GYKOEF*(ro[m3-1]+ro[m3-ynumy-1])/2.0;}
  }
 }
 gridcheck();snprintf(fl1out,50,"%s",fl1in);fl1otp=fl1itp;printmod=1;saver(0,0);
 dynmemall(3);dynmemall(4);dynmemall(5);
 puts("chatGFD coupled material fields rebuilt without time evolution");return 0;
}
