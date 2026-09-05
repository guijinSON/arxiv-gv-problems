import random, time

PAIRINGS = (((0,1),(2,3)), ((0,2),(1,3)), ((0,3),(1,2)))

def make(n, seed=0):
    assert n % 3 == 0
    rng=random.Random(seed)
    groups=list(range(n)); rng.shuffle(groups)
    A=set(groups[:2*n//3])
    ranks_list=[(g,p) for g in groups for p in (0,1)]
    rng.shuffle(ranks_list)
    rank={x:i for i,x in enumerate(ranks_list)}
    slots=[]
    for g in groups:
        for j in range(1 if g in A else 2): slots.append((g,j))
    stubs=[(g,p) for g in A for p in (0,1)]
    rng.shuffle(slots); rng.shuffle(stubs)
    # randomized Kuhn perfect matching
    adj=[]
    for d,j in slots:
        lo,hi=sorted((rank[d,0],rank[d,1]))
        a=[k for k,s in enumerate(stubs) if rank[s] < lo or rank[s] > hi]
        rng.shuffle(a); adj.append(a)
    mt=[-1]*len(stubs)
    def aug(i, seen):
        for k in adj[i]:
            if seen[k]: continue
            seen[k]=1
            if mt[k]<0 or aug(mt[k],seen):
                mt[k]=i; return True
        return False
    order=list(range(len(slots))); rng.shuffle(order)
    for i in order:
        if not aug(i,[0]*len(stubs)): return make(n,seed+1000003)
    sm=[None]*len(slots)
    for k,i in enumerate(mt): sm[i]=stubs[k]
    latent=[]
    for i,((d,j),s) in enumerate(zip(slots,sm)):
        occ=[(d,0),(d,1),s]
        occ.sort(key=lambda x:rank[x], reverse=True) # bottom to top
        latent.append(occ)
    # rename groups, ids, stacks
    gp=list(range(n)); rng.shuffle(gp); rename={g:gp[g] for g in range(n)}
    tile_records=[]
    for si,stack in enumerate(latent):
        for h,node in enumerate(stack): tile_records.append((si,h,node))
    ids=list(range(4*n)); rng.shuffle(ids)
    stacks=[[None]*3 for _ in latent]; tile_group=[None]*(4*n); tile_node={}
    for tid,(si,h,node) in zip(ids,tile_records):
        stacks[si][h]=tid; tile_group[tid]=rename[node[0]]; tile_node[tid]=node
    rng.shuffle(stacks)
    inst={'n':n,'stacks':stacks,'tile_groups':tile_group}
    bits=[]
    for g in range(n):
        tids=sorted(i for i,x in enumerate(tile_group) if x==g)
        pos={t:(si,h) for si,st in enumerate(stacks) for h,t in enumerate(st)}
        opts=[]
        for pairs in PAIRINGS:
            pp=[(tids[a],tids[b]) for a,b in pairs]
            if all(pos[a][0]!=pos[b][0] for a,b in pp): opts.append(pp)
        planted={frozenset((a,b)) for a,b in opts[0] if tile_node[a]==tile_node[b]}
        choice=0 if len(planted)==2 else 1
        if choice==1:
            assert all(tile_node[a]==tile_node[b] for a,b in opts[1])
        bits.append(str(choice))
    inst['answer']=''.join(bits)
    return inst

def options(inst):
    n=inst['n']; tg=inst['tile_groups']; stacks=inst['stacks']
    pos={t:(si,h) for si,st in enumerate(stacks) for h,t in enumerate(st)}
    out=[]
    for g in range(n):
        tids=sorted(i for i,x in enumerate(tg) if x==g)
        opts=[]
        for pairing in PAIRINGS:
            pp=tuple((tids[a],tids[b]) for a,b in pairing)
            if all(pos[a][0]!=pos[b][0] for a,b in pp): opts.append(pp)
        assert len(opts)==2
        out.append(opts)
    return out

def verify(inst,bits):
    n=inst['n']
    if not isinstance(bits,str) or len(bits)!=n or any(x not in '01' for x in bits): return False
    opts=options(inst); node={}; k=0
    for g,b in enumerate(bits):
        for a,c in opts[g][int(b)]: node[a]=node[c]=k; k+=1
    adj=[set() for _ in range(2*n)]; indeg=[0]*(2*n)
    for st in inst['stacks']:
        for lower,upper in zip(st,st[1:]):
            u,v=node[upper],node[lower]
            if u==v:return False
            if v not in adj[u]:adj[u].add(v);indeg[v]+=1
    q=[i for i,d in enumerate(indeg) if d==0]
    for u in q:
        for v in adj[u]:
            indeg[v]-=1
            if indeg[v]==0:q.append(v)
    return len(q)==2*n

def partial_cycle(inst, assigned, opts):
    node={}; k=0
    for g,b in assigned.items():
        for a,c in opts[g][b]:node[a]=node[c]=k;k+=1
    adj=[set() for _ in range(k)]; indeg=[0]*k
    for st in inst['stacks']:
        for lo,up in zip(st,st[1:]):
            if lo in node and up in node:
                u,v=node[up],node[lo]
                if u==v:return True
                if v not in adj[u]:adj[u].add(v);indeg[v]+=1
    q=[i for i,d in enumerate(indeg) if d==0]
    for u in q:
        for v in adj[u]:
            indeg[v]-=1
            if indeg[v]==0:q.append(v)
    return len(q)<k

def dfs(inst, cap=100000, heuristic=True):
    opts=options(inst); n=inst['n']; assigned={}; nodes=0
    # incidence neighbors
    tg=inst['tile_groups']; neigh=[set() for _ in range(n)]
    for st in inst['stacks']:
        gs=[tg[t] for t in st]
        for a,b in zip(gs,gs[1:]):
            if a!=b:neigh[a].add(b);neigh[b].add(a)
    def rec():
        nonlocal nodes
        if nodes>=cap:return None
        nodes+=1
        if len(assigned)==n:
            b=''.join(str(assigned[g]) for g in range(n))
            return b if verify(inst,b) else False
        un=[g for g in range(n) if g not in assigned]
        if heuristic:
            g=max(un,key=lambda x:(sum(y in assigned for y in neigh[x]),len(neigh[x])))
        else:g=un[0]
        for b in (0,1):
            assigned[g]=b
            if not partial_cycle(inst,assigned,opts):
                r=rec()
                if r not in (False,None):return r
                if r is None and nodes>=cap:del assigned[g];return None
            del assigned[g]
        return False
    t=time.perf_counter();ans=rec();return ans,nodes,time.perf_counter()-t

if __name__=='__main__':
  for n in (12,24,36,48,60,72):
    vals=[]
    for seed in range(4):
      x=make(n,seed); assert verify(x,x['answer'])
      hits=sum(verify(x,''.join(random.Random(seed*1000+j).choice('01') for _ in range(n))) for j in range(1000))
      a,nodes,sec=dfs(x,100000)
      vals.append((hits,nodes,round(sec,3),a is not None and a is not False))
    print(n,vals)
