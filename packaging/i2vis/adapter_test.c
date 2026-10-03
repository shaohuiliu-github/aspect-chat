/* Nonsymmetric analytic system: detects accidentally solving A^T x=b. */
#include <mkl.h>
int main(void){
 void *pt[64]={0};int maxfct=1,mnum=1,mtype=11,n=3,nrhs=1,iparm[64]={0},perm[3]={0},msglvl=0,error=0;
 int ia[]={1,3,5,7},ja[]={1,2,2,3,1,3};double a[]={2,1,3,1,1,4},b[]={4,9,13},x[3]={0};
 int phases[]={11,22,33};
 for(int i=0;i<3;i++){int phase=phases[i];PARDISO(pt,&maxfct,&mnum,&mtype,&phase,&n,a,ia,ja,perm,&nrhs,iparm,&msglvl,b,x,&error);if(error)return 1;}
 for(int i=0;i<3;i++)if(fabs(x[i]-(i+1))>1e-12)return 2;
 int phase=-1;PARDISO(pt,&maxfct,&mnum,&mtype,&phase,&n,a,ia,ja,perm,&nrhs,iparm,&msglvl,b,x,&error);
 puts("chatGFD nonsymmetric adapter test passed");return error?3:0;
}
