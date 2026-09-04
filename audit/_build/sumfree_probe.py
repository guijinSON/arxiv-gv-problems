import importlib.util, sys, time
def load(p,name):
    s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
R="/private/tmp/claude-501/-Users-songuijin-claude-aug/239a527d-78de-4edb-a803-387c36f15c2a/scratchpad/arxiv-gv-problems/results/"
g=load(R+"2502.08624/gen_2502_08624.py","g3")
p=g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
t=time.time(); inst=g.make_instance(seed=0,**p); print("build %.2fs"%(time.time()-t))
A=inst["numbers"]; print("|A|",len(A),"del",inst["deletion_count"],"target",inst["target_size"])
print("private keys:",[k for k in inst if k.startswith("_")])
t=time.time()
vals=sorted(A); present=set(vals)
rels=[]
for i,x in enumerate(vals):
    for y in vals[i:]:
        z=x+y
        if z in present: rels.append((x,y,z))
print("relations %d in %.2fs"%(len(rels),time.time()-t))
ops={u for x,y,_ in rels for u in (x,y)}
res={z for _,_,z in rels}
print("operands",len(ops),"results-only",len(res-ops),"overlap",len(res&ops))
