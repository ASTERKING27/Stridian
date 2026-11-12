poly=[(92,22),(79.48,19.33),(23.99,24.77),(10.0,62.24),(58.46,67.08),(35.34,85.15),(28,96),(40.66,92.65),(95.78,57.42),(28.92,49.77),(32.54,34.97),(80.52,27.67)]
head=[(64.5,3.2),(68.8,10),(60.8,16.4),(56.6,9.4)]
def inside(pt,pg):
    x,y=pt;c=False
    for i in range(len(pg)):
        x1,y1=pg[i];x2,y2=pg[i-1]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c
for r in range(0,50):
    y=r*2+1
    print(''.join('##' if (inside((c*2+1,y),poly) or inside((c*2+1,y),head)) else '  ' for c in range(50)))
