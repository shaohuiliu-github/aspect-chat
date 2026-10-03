/* Portable adapter for I2VIS's nonsymmetric, one-based CSR PARDISO calls.
 * The scientific assembly is unchanged. SuiteSparse UMFPACK replaces MKL.
 * CSR(A) is CSC(A^T); solve with UMFPACK_At, not UMFPACK_A.
 * Backend and residual are recorded; this is not a claim of MKL equivalence. */
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <umfpack.h>
typedef struct {int *ap,*ai;void *symbolic,*numeric;double control[UMFPACK_CONTROL];} chatgfd_lu;
static void PARDISO(void **pt,int *maxfct,int *mnum,int *mtype,int *phase,int *n,double *a,int *ia,int *ja,int *perm,int *nrhs,int *iparm,int *msglvl,double *b,double *x,int *error){
 *error=0; chatgfd_lu *s=(chatgfd_lu*)pt[0];
 if(*phase==11){
  if(*mtype!=11||*nrhs!=1||ia[0]!=1){*error=-1;return;}
  s=calloc(1,sizeof(*s));pt[0]=s;if(!s){*error=-2;return;}
  s->ap=malloc((*n+1)*sizeof(int));s->ai=malloc((ia[*n]-1)*sizeof(int));
  if(!s->ap||!s->ai){*error=-2;return;}
  for(int i=0;i<=*n;i++)s->ap[i]=ia[i]-1;
  for(int i=0;i<ia[*n]-1;i++)s->ai[i]=ja[i]-1;
  umfpack_di_defaults(s->control);s->control[UMFPACK_IRSTEP]=20;
  *error=umfpack_di_symbolic(*n,*n,s->ap,s->ai,a,&s->symbolic,s->control,NULL);
 }else if(*phase==22){*error=umfpack_di_numeric(s->ap,s->ai,a,s->symbolic,&s->numeric,s->control,NULL);
  if(*error!=0){int empty=0;for(int i=0;i<*n;i++)empty+=(s->ap[i]==s->ap[i+1]);printf("\nchatGFD factorization n=%d nnz=%d empty_rows=%d\n",*n,s->ap[*n],empty);FILE *f=fopen("failed-matrix.txt","w");if(f){for(int i=0;i<*n;i++)for(int j=s->ap[i];j<s->ap[i+1];j++)fprintf(f,"%d %d %.17g\n",i,s->ai[j],a[j]);fclose(f);}}
 }else if(*phase==33){
  *error=umfpack_di_solve(UMFPACK_At,s->ap,s->ai,a,x,b,s->numeric,s->control,NULL);
  if(*error==0){double residual=0,scale=0;
   for(int i=0;i<*n;i++){double ax=0,sum=0;for(int j=s->ap[i];j<s->ap[i+1];j++){ax+=a[j]*x[s->ai[j]];sum+=fabs(a[j]*x[s->ai[j]]);}residual=fmax(residual,fabs(ax-b[i]));scale=fmax(scale,sum+fabs(b[i]));}
   double rel=residual/fmax(scale,1e-300);printf("\nchatGFD backend=UMFPACK backward_error=%.6e\n",rel);if(!isfinite(rel)||rel>1e-8)*error=-99;
  }
 }else if(*phase==-1){if(s){umfpack_di_free_symbolic(&s->symbolic);umfpack_di_free_numeric(&s->numeric);free(s->ap);free(s->ai);free(s);}pt[0]=NULL;
 }else *error=-1;
}
