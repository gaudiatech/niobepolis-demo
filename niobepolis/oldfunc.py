

my_x, my_y = 0, 0  # comme un offset purement 2d -> utile pr camera
posdecor = list()
vscr_size = None


def gridbased_2d_disp(screen, grid_spec, coords, ref_img):
    local_i, local_j = coords
    screen.blit(ref_img, (my_x + local_i * grid_spec[0], my_y + local_j * grid_spec[1]))


def realise_pavage(screen, gfx_elt, offsets=(0, 0)):
    global vscr_size
    incx, incy = gfx_elt.get_size()  # 64*32 pour floortile
    for y in range(0, vscr_size[1], incy):
        for x in range(0, vscr_size[0], incx):
            screen.blit(gfx_elt, (offsets[0] + x, offsets[1] + y))


def conv_map_coords_floorgrid(u, v, z):
    base_res = [4, 0]  # mapcoords 0,0
    while u > 0:
        u -= 1
        base_res[0] += 1
        base_res[1] += 1
    while v > 0:
        v -= 1
        base_res[0] -= 1
        base_res[1] += 1
    while z > 0:
        z -= 1
        base_res[1] -= 1
    return base_res
