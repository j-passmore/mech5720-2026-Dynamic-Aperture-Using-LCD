# Sprites

These are the character frames the custom bokeh drew on the panel. [make_sprites.py](make_sprites.py)
writes every frame, GIF and APNG from character grids, one cell per sprite pixel, and scales each
grid to the 128 x 160 panel by nearest-neighbour sampling. `binary/` holds a transparent
character on black. `grey/` holds the same frames with some regions at mid-grey. The report used
`binary/` only.

| Folder | Frames | Game | Developer and year | Used in the report |
| --- | --- | --- | --- | --- |
| `mario/` | `mario_binary_walk_1` to `3` | Super Mario Bros. | Nintendo, 1985 | Yes |
| `link/` | `link_binary_attack_1` and `2`, `link_binary_walk_1` and `2` | The Legend of Zelda | Nintendo, 1986 | Attack frames only |
| `knight/` | `knight_binary_walk_1` and `2` | Realm of the Mad God | Wild Shadow Studios and Spry Fox, 2010 | Yes |
| `terraria/` | `terraria_binary_mine_1` and `2` | Terraria | Re-Logic, 2011 | No |

## Where each frame came from

- **Mario** is the three-frame walk cycle of Super Mario Bros., in playback order.
- **Link** walks in the pose of the Zelda Wiki's "TLoZ Link Sprite 3". The attack frames are the
  walking stance mirrored, since the game flips the sprite for left, and the sword thrust.
- **The Knight** is the 8 x 8 Knight of Realm of the Mad God, seen from the side.
- **The Terraria miner** holds the pickaxe raised in frame 1 and swings it through 180 degrees
  about the shoulder in frame 2. The group did not photograph it.

## Rights

The artwork belongs to the rights holders. The group redrew each frame as a low-resolution
binary mask for study and does not claim the designs. The [MIT Licence](../../../../LICENSE) of this
repository covers the code and the group's photographs, not these characters.
