VECADD = "vecadd"
VECMUL = "vecmul"
VECSUB = "vecsub"
VECDIV = "vecdiv"

VECNEG = "vecneg"

VECMAC = "vecmac"

VECLOAD = "vecload"
VECSTORE = "vecstore"

VECZERO = "veczero"

VECMOVE = "vecmove"

VEC_BINOPS = [VECADD, VECMUL, VECSUB, VECDIV]
VEC_UNOPS = [VECNEG, VECMOVE]
VEC_OPS = [VECMAC, *VEC_UNOPS, *VEC_BINOPS]

VECTOR = "vector"

VECTOR_LANE_WIDTH = 4
