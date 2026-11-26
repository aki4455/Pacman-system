import logging
import traceback
import cv2
import numpy as np
from maps.classic import classic

OBJECT_ALIES = {"P":(0, 255, 0), "G":(0, 0, 255), "#":(255, 0, 0), ".":(0,0,0)}

def render_map(grid: list[list[str]], cell:int = 24) -> np.ndarray:
    h, w = len(grid), len(grid[0])
    img = np.zeros((h,w,3), np.uint8)
    for x in range(h):
        for i in range(w):
            img[x,i] = OBJECT_ALIES[grid[x][i]]
    
    cv2.imwrite("result.png", img)
    
    
def main():
    rendered = render_map(classic)
    
    
    
if __name__ == "__main__":
    main()