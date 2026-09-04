/* mitm4.c -- exhaustive 4-list meet-in-the-middle for balanced +-1 zero sums.
 *
 * Reads:  n  (multiple of 4, <= 64)
 *         w_0 .. w_{n-1}   unsigned 64-bit decimal, arithmetic is mod 2^64
 * Finds:  every c in {+1,-1}^n with  sum_i c_i w_i == 0  (mod 2^64), up to the
 *         global sign symmetry c <-> -c (coordinate 0 is pinned to +1).
 * Prints: "MASK <hex>"   bit i set  <=>  c_i = -1
 *
 * Split the n coordinates into four blocks of B = n/4.  Enumerate the 2^B block
 * sums of each block, bucket them by their low MBITS bits, and for every residue
 * class r pair (block0,block1) sums with low bits r against (block2,block3) sums
 * with low bits -r, matching the full 64 bits in a cache-resident open-addressed
 * table.  Time ~ 1.5 * 2^(n/2), memory ~ 2^(n/2-MBITS).  Schroeppel-Shamir with a
 * modular filter: exhaustive, no heuristic pruning.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>

static int N, B, MBITS, HBITS, NTHREADS;
static uint64_t W[64];
static uint32_t LSZ[4];
static uint64_t *bval[4];   /* block sums, in bucket order (sequential reads) */
static uint32_t *bmask[4];  /* the corresponding block sign mask */
static uint32_t *bstart[4];

static pthread_mutex_t outmu = PTHREAD_MUTEX_INITIALIZER;

static void build_lists(void) {
    uint32_t nb = 1u << MBITS;
    for (int j = 0; j < 4; j++) {
        int nfree = (j == 0) ? B - 1 : B;      /* pin coordinate 0 to +1 */
        int off = j * B + (j == 0 ? 1 : 0);
        uint32_t sz = 1u << nfree;
        LSZ[j] = sz;
        uint64_t *v = (uint64_t *)malloc((size_t)sz * sizeof(uint64_t));
        uint64_t base = 0;
        for (int t = 0; t < B; t++) base += W[j * B + t];
        v[0] = base;
        for (uint32_t s = 1; s < sz; s++) {
            int t = __builtin_ctz(s);
            v[s] = v[s & (s - 1)] - 2ULL * W[off + t];
        }
        bstart[j] = (uint32_t *)calloc(nb + 1, sizeof(uint32_t));
        bval[j] = (uint64_t *)malloc((size_t)sz * sizeof(uint64_t));
        bmask[j] = (uint32_t *)malloc((size_t)sz * sizeof(uint32_t));
        for (uint32_t s = 0; s < sz; s++) bstart[j][(v[s] & (nb - 1)) + 1]++;
        for (uint32_t b = 0; b < nb; b++) bstart[j][b + 1] += bstart[j][b];
        uint32_t *fill = (uint32_t *)malloc(nb * sizeof(uint32_t));
        memcpy(fill, bstart[j], nb * sizeof(uint32_t));
        for (uint32_t s = 0; s < sz; s++) {
            uint32_t p = fill[v[s] & (nb - 1)]++;
            bval[j][p] = v[s];
            bmask[j][p] = (j == 0) ? (s << 1) : s;   /* undo the pinned bit */
        }
        free(fill);
        free(v);
    }
}

typedef struct {
    uint64_t *keys;
    uint32_t *va, *vb;
    uint8_t *occ;
    uint32_t *used;
    int tid;
} thr_t;

static void *worker(void *arg) {
    thr_t *T = (thr_t *)arg;
    const uint32_t HM = (1u << HBITS) - 1;
    const int sh = 64 - HBITS;
    const uint32_t nb = 1u << MBITS, bm = nb - 1;
    const int mb = MBITS;
    char buf[1 << 16];
    int buflen = 0;
    uint64_t *keys = T->keys;
    uint32_t *va = T->va, *vb = T->vb, *used = T->used;
    uint8_t *occ = T->occ;

    for (uint32_t r = (uint32_t)T->tid; r < nb; r += (uint32_t)NTHREADS) {
        uint32_t nused = 0;
        for (uint32_t b0 = 0; b0 < nb; b0++) {
            uint32_t s0 = bstart[0][b0], e0 = bstart[0][b0 + 1];
            if (s0 == e0) continue;
            uint32_t b1 = (r - b0) & bm;
            uint32_t s1 = bstart[1][b1], e1 = bstart[1][b1 + 1];
            if (s1 == e1) continue;
            for (uint32_t p = s0; p < e0; p++) {
                uint64_t a = bval[0][p];
                uint32_t ma = bmask[0][p];
                for (uint32_t q = s1; q < e1; q++) {
                    uint64_t key = a + bval[1][q];
                    uint32_t h = (uint32_t)(((key >> mb) * 0x9E3779B97F4A7C15ULL) >> sh);
                    while (occ[h]) h = (h + 1) & HM;
                    occ[h] = 1;
                    keys[h] = key;
                    va[h] = ma;
                    vb[h] = bmask[1][q];
                    used[nused++] = h;
                }
            }
        }
        uint32_t r2 = (0u - r) & bm;
        for (uint32_t b2 = 0; b2 < nb; b2++) {
            uint32_t s2 = bstart[2][b2], e2 = bstart[2][b2 + 1];
            if (s2 == e2) continue;
            uint32_t b3 = (r2 - b2) & bm;
            uint32_t s3 = bstart[3][b3], e3 = bstart[3][b3 + 1];
            if (s3 == e3) continue;
            for (uint32_t p = s2; p < e2; p++) {
                uint64_t a = bval[2][p];
                uint32_t mc = bmask[2][p];
                for (uint32_t q = s3; q < e3; q++) {
                    uint64_t key = 0ULL - (a + bval[3][q]);
                    uint32_t h = (uint32_t)(((key >> mb) * 0x9E3779B97F4A7C15ULL) >> sh);
                    while (occ[h]) {
                        if (keys[h] == key) {
                            uint64_t mask = (uint64_t)va[h]
                                          | ((uint64_t)vb[h] << B)
                                          | ((uint64_t)mc << (2 * B))
                                          | ((uint64_t)bmask[3][q] << (3 * B));
                            buflen += snprintf(buf + buflen, sizeof(buf) - buflen,
                                               "MASK %016llx\n",
                                               (unsigned long long)mask);
                            if (buflen > (int)sizeof(buf) - 64) {
                                pthread_mutex_lock(&outmu);
                                fwrite(buf, 1, buflen, stdout);
                                pthread_mutex_unlock(&outmu);
                                buflen = 0;
                            }
                        }
                        h = (h + 1) & HM;
                    }
                }
            }
        }
        for (uint32_t i = 0; i < nused; i++) occ[used[i]] = 0;
    }
    if (buflen) {
        pthread_mutex_lock(&outmu);
        fwrite(buf, 1, buflen, stdout);
        pthread_mutex_unlock(&outmu);
    }
    return NULL;
}

int main(int argc, char **argv) {
    if (scanf("%d", &N) != 1) return 1;
    for (int i = 0; i < N; i++) {
        unsigned long long v;
        if (scanf("%llu", &v) != 1) return 1;
        W[i] = (uint64_t)v;
    }
    if (N % 4 || N > 64 || N < 8) { fprintf(stderr, "n must be a multiple of 4 in [8,64]\n"); return 1; }
    B = N / 4;
    MBITS = (argc > 1) ? atoi(argv[1]) : (2 * B - 16 > 1 ? 2 * B - 16 : 1);
    NTHREADS = (argc > 2) ? atoi(argv[2]) : 8;
    if (MBITS > 2 * B - 1) MBITS = 2 * B - 1;
    { int cls = 2 * B - 1 - MBITS; HBITS = cls + 2; if (HBITS < 8) HBITS = 8; if (HBITS > 26) HBITS = 26; }
    if ((1 << MBITS) < NTHREADS) NTHREADS = 1 << MBITS;
    fprintf(stderr, "n=%d B=%d MBITS=%d HBITS=%d threads=%d\n", N, B, MBITS, HBITS, NTHREADS);
    build_lists();
    pthread_t th[64];
    thr_t T[64];
    uint32_t H = 1u << HBITS;
    for (int t = 0; t < NTHREADS; t++) {
        T[t].keys = (uint64_t *)malloc((size_t)H * sizeof(uint64_t));
        T[t].va = (uint32_t *)malloc((size_t)H * sizeof(uint32_t));
        T[t].vb = (uint32_t *)malloc((size_t)H * sizeof(uint32_t));
        T[t].occ = (uint8_t *)calloc(H, 1);
        T[t].used = (uint32_t *)malloc((size_t)H * sizeof(uint32_t));
        T[t].tid = t;
    }
    for (int t = 0; t < NTHREADS; t++) pthread_create(&th[t], NULL, worker, &T[t]);
    for (int t = 0; t < NTHREADS; t++) pthread_join(th[t], NULL);
    fflush(stdout);
    return 0;
}
