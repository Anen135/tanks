import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from art import Sprites

pygame.init()
pygame.display.set_mode((16, 16))
sp = Sprites()
sheet = pygame.Surface((6 * 20, 40))
sheet.fill((30, 30, 40))
for i, (k, icon) in enumerate(sp.power_icons.items()):
    sheet.blit(icon, (i * 20 + 2, 2))
for i, style in enumerate(("player", "basic", "fast", "power", "armor4", "armor3",
                           "armor2", "armor1", "bonus")):
    sheet.blit(sp.tank(style, 0, 0), (i * 20 + 2, 20))
pygame.image.save(pygame.transform.scale(sheet, (sheet.get_width() * 8,
                                                 sheet.get_height() * 8)),
                  "icons.png")
print("ok")
pygame.quit()
