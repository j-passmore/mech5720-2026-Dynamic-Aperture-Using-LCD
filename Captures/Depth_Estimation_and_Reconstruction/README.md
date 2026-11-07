# Depth estimation and reconstruction photos

Both depth methods and both reconstruction scripts read the photos in this folder.
[The depth README](../../App/Processing/I-Depth_Estimation/README.md) lists every file and what
reads it. The group shot all of them at 2 s, ISO 200 and f/5 with the lens near 35 mm.

- `fpn/` holds ten lens cap dark frames.
- `Scale_1/psfs_v2/` holds the PSF set the report used, a torch at five distances through each mask.
- `Scale_1/psfs/` holds the first PSF set, which clipped in every photo.
- `Scale_1/mask1.CR2` and `Scale_1/mask2.CR2` hold the scene pair from 25 October.
- `ambient/` holds ten ambient frames and `black_lvl.CR2` one black level frame.
- `distances.yaml` gives the distance of each PSF.
