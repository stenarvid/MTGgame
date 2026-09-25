import pygame

def draw_node_icon(screen, node_type, x, y):
    """Draws clean vector-style geometric icons for map nodes."""
    if node_type == "Combat":
        pygame.draw.line(screen, (255, 255, 255), (x - 6, y - 6), (x + 6, y + 6), 2)
        pygame.draw.line(screen, (255, 255, 255), (x - 6, y + 6), (x + 6, y - 6), 2)
    elif node_type == "Elite":
        points = [(x, y - 8), (x + 7, y), (x, y + 8), (x - 7, y)]
        pygame.draw.polygon(screen, (255, 100, 100), points, 2)
        pygame.draw.circle(screen, (255, 100, 100), (x, y), 2)
    elif node_type == "Merchant":
        points = [(x, y - 8), (x + 6, y), (x, y + 8), (x - 6, y)]
        pygame.draw.polygon(screen, (255, 215, 0), points, 2)
    elif node_type == "Rest":
        points = [(x, y + 6), (x - 6, y - 4), (x + 6, y - 4)]
        pygame.draw.polygon(screen, (100, 220, 255), points, 2)
    elif node_type == "Treasure":
        pygame.draw.rect(screen, (200, 100, 255), (x - 5, y - 5, 10, 10), 2)
    elif node_type == "Boss":
        points = [(x - 8, y + 4), (x - 8, y - 4), (x - 4, y), (x, y - 7), (x + 4, y), (x + 8, y - 4), (x + 8, y + 4)]
        pygame.draw.polygon(screen, (255, 50, 50), points, 2)

def draw_wrapped_text(screen, text, font, color, x, y, max_width):
    """Utility to wrap and draw text within a specific pixel width."""
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)
    
    for i, line in enumerate(lines):
        txt_surface = font.render(line, True, color)
        screen.blit(txt_surface, (x, y + (i * 18)))
    return len(lines) * 18

