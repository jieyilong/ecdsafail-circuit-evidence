/* Exact signed-integer recurrence, without circuit truncation or phase modeling. */
#include <gmp.h>
#include <stdio.h>
#include <stdlib.h>

static int width(int k,int margin) {
    int w=k<40 ? 256+margin-17*k/100 : k<304 ? 250+margin-33*(k-40)/100 : 163+margin-40*(k-304)/100;
    return w<8?8:w>259?259:w;
}
static int fits(mpz_t x,int w) {
    size_t bits=mpz_sizeinbase(x,2);
    return bits<(size_t)w || (mpz_sgn(x)<0 && bits==(size_t)w && mpz_scan1(x,0)==(mp_bitcnt_t)(w-1));
}
int main(int argc,char **argv) {
    if(argc!=3) return 2;
    FILE *f=fopen(argv[1],"rb"); if(!f) return 3;
    unsigned long n=strtoul(argv[2],0,10),hist[802]={0},bad[2]={0},sum=0;
    mpz_t p,h,d,u,v,t,one;
    mpz_inits(p,h,d,u,v,t,one,NULL);
    mpz_set_ui(p,1);mpz_mul_2exp(p,p,256);mpz_set_ui(t,1);mpz_mul_2exp(t,t,32);mpz_sub(p,p,t);mpz_sub_ui(p,p,977);
    mpz_add_ui(h,p,1);mpz_fdiv_q_2exp(h,h,1);mpz_set_ui(one,1);
    for(unsigned long i=0;i<n;i++) {
        unsigned char bytes[32];if(fread(bytes,1,32,f)!=32) return 4;
        mpz_import(d,32,1,1,0,0,bytes);
        if(mpz_sgn(d)==0 || mpz_cmp(d,p)>=0) return 5;
        mpz_set(u,p);mpz_set(v,d);int first=801,miss[2]={0};
        for(int k=0;k<800;k++) {
            for(int g=0;g<2;g++) if(k<(g?736:704) && (!fits(u,width(k,g?20:4))||!fits(v,width(k,g?20:4)))) miss[g]=1;
            if(k==0) {
                int a0=mpz_tstbit(d,0),a1=mpz_tstbit(d,1);
                mpz_fdiv_q_2exp(v,d,1);mpz_sub(v,v,p);if(a1)mpz_add(v,v,p);if(a0)mpz_add(v,v,h);
            } else {
                mpz_ptr target=k%2?u:v,source=k%2?v:u;
                int sign=mpz_tstbit(source,1)^mpz_tstbit(target,1);
                if(sign)mpz_sub(t,target,source);else mpz_add(t,target,source);
                for(int g=0;g<2;g++) if(k<(g?736:704)&&!fits(t,width(k,g?20:4)))miss[g]=1;
                mpz_fdiv_q_2exp(target,t,1);
            }
            if(mpz_cmpabs(u,one)==0 && mpz_cmpabs(v,one)==0) {first=k+1;break;}
        }
        hist[first]++;sum+=first;bad[0]+=miss[0];bad[1]+=miss[1];
    }
    printf("{\"n\":%lu,\"censored_at_801\":%lu,\"round_sum_censored\":%lu,\"original_width_misses\":%lu,\"conservative_width_misses\":%lu,\"histogram\":{",n,hist[801],sum,bad[0],bad[1]);
    int sep=0;for(int k=0;k<=801;k++)if(hist[k]){printf("%s\"%d\":%lu",sep?",":"",k,hist[k]);sep=1;}
    printf("}}\n");fclose(f);mpz_clears(p,h,d,u,v,t,one,NULL);return 0;
}
