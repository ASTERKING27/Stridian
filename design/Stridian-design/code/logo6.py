import math
from shapely.geometry import Polygon, Point
P=[(90,35),(85,19),(27,27),(18,55),(87,60),(38,93),(8,84)]   # knee pushed forward, heel->toe tail stretched out
W=[0,5.0,6.3,7.6,7.4,5.2,0]
def sub(a,b):return(a[0]-b[0],a[1]-b[1])
def add(a,b):return(a[0]+b[0],a[1]+b[1])
def mul(a,k):return(a[0]*k,a[1]*k)
def norm(a):
    l=math.hypot(*a);return(a[0]/l,a[1]/l)
def nrm(a,b):
    d=norm(sub(b,a));return(-d[1],d[0])
def inter(p1,d1,p2,d2):
    den=d1[0]*d2[1]-d1[1]*d2[0]
    t=((p2[0]-p1[0])*d2[1]-(p2[1]-p1[1])*d2[0])/den
    return add(p1,mul(d1,t))
def side(s):
    pts=[]
    for i in range(len(P)):
        if W[i]==0: pts.append(P[i]);continue
        a,b,c=P[i-1],P[i],P[i+1]
        n1=mul(nrm(a,b),s);n2=mul(nrm(b,c),s)
        l1p=add(a,mul(n1,W[i-1]));l1q=add(b,mul(n1,W[i]))
        l2p=add(b,mul(n2,W[i]));l2q=add(c,mul(n2,W[i+1]))
        pts.append(inter(l1p,sub(l1q,l1p),l2p,sub(l2q,l2p)))
    return pts
poly=side(1)+side(-1)[::-1][1:-1]
xs=[p[0] for p in poly];ys=[p[1] for p in poly]
bx=(min(xs)+max(xs))/2;by=(min(ys)+max(ys))/2
sc=94/max(max(xs)-min(xs),max(ys)-min(ys))
T=lambda p:(50+(p[0]-bx)*sc,50+(p[1]-by)*sc)
S=Polygon([T(p) for p in poly]); K=[T(p) for p in P]
u=(-math.cos(math.radians(40)),math.sin(math.radians(40))); n=(u[1],-u[0])
def band(pt,g,B):
    return Polygon([(pt[0]+u[0]*B+n[0]*g/2,pt[1]+u[1]*B+n[1]*g/2),(pt[0]-u[0]*B+n[0]*g/2,pt[1]-u[1]*B+n[1]*g/2),
                    (pt[0]-u[0]*B-n[0]*g/2,pt[1]-u[1]*B-n[1]*g/2),(pt[0]+u[0]*B-n[0]*g/2,pt[1]+u[1]*B-n[1]*g/2)])
def tipcut(tip,prev,back):
    d=norm(sub(tip,prev)); c=sub(tip,mul(d,back))
    s=1 if d[0]*n[0]+d[1]*n[1]>0 else -1
    hp=band(add(c,mul(n,s*50)),100,300)
    return hp.intersection(Point(*tip).buffer(7))
S=S.difference(tipcut(K[0],K[1],3.5*sc/ (94/ (97-3)) if False else 3.5))
S=S.difference(tipcut(K[6],K[5],3.5))
f=.616; ac=(K[2][0]+(K[1][0]-K[2][0])*f, K[2][1]+(K[1][1]-K[2][1])*f+.85)
top=max(K[1][1],K[2][1])+9
S=S.difference(band(ac,2.4,60).intersection(Polygon([(0,-10),(110,-10),(110,top),(0,top)])))
geoms=list(S.geoms) if S.geom_type=='MultiPolygon' else [S]
print(len(geoms),'pieces',[round(g.area,1) for g in geoms])
for r in range(50):
    print(''.join('##' if S.contains(Point(c*2+1,r*2+1)) else '  ' for c in range(50)))
d=''.join('M'+'L'.join(f'{x:.1f} {y:.1f}' for x,y in list(g.exterior.coords)[:-1])+'Z' for g in sorted(geoms,key=lambda g:-g.area))
print('D',d)
print('SKEL',[(round(x,1),round(y,1)) for x,y in K])
C,Dk=K[3],K[4];print('ANCHOR',round((C[0]+Dk[0])/2,1),round((C[1]+Dk[1])/2,1))
print('bounds',S.bounds)
