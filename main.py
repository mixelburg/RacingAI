import datetime

import math
import neat
import pygame
from random import choice
import os
import json
import concurrent.futures

pygame.init()

with open("main-config.json") as main_config:
    config = json.load(main_config)

TRANSPARENT_PIXEL = config["transparent_pixel"]

GAME_WINDOW_RESOLUTION = config["main"]["resolutions"]["game_window"]
MAIN_WINDOW_RESOLUTION = (int(GAME_WINDOW_RESOLUTION[0] * config["main"]["resolutions"]["main_window"][0]),
                          int(GAME_WINDOW_RESOLUTION[1] * config["main"]["resolutions"]["main_window"][1]))

FRAME_RATE = config["main"]["frame_rate"]

IMG_SRC_FOLDER = config["main"]["img_src_folder"]

CAR_INITIAL_SIZE = config["car"]["car_init_size"]
CAR_SIZE = MAIN_WINDOW_RESOLUTION[0] * config["car"]["car_size"]
CAR_IMGS = [
    pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER, config["car"]["img"].format(i + 1))),
                           (int(CAR_INITIAL_SIZE[0] * CAR_SIZE), int(CAR_INITIAL_SIZE[1] * CAR_SIZE)))
    for i in range(config["car"]["num_cars_imgs"])
]

BG_IMG = pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER,
                                                               config["main"]["imgs"]["surroundings"])),
                                GAME_WINDOW_RESOLUTION)

MAIN_BG_IMG = pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER,
                                                                    config["main"]["imgs"]["main_bg"])),
                                     GAME_WINDOW_RESOLUTION)
TRACK = pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER,
                                                              config["main"]["imgs"]["track"])),
                               GAME_WINDOW_RESOLUTION)

ARROW_INITIAL_SIZE = config["radar"]["arrow"]["arrow_init_size"]
ARROW_SIZE = config["radar"]["arrow"]["arrow_size"] * CAR_SIZE
ARROW_IMG = pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER, config["radar"]["arrow"]["img"])),
                                   (int(ARROW_INITIAL_SIZE[0] * ARROW_SIZE), int(ARROW_INITIAL_SIZE[1] * ARROW_SIZE)))

RADAR_ANGLES = config["radar"]["angles"]
RADAR_MAX_LEN = config["radar"]["max_len"]
RADAR_BEAM_THICKNESS = config["radar"]["beam_thickness"]

BG_POSITION = config["main"]["imgs"]["position"]
TRACK_POSITION = BG_POSITION
CAR_POSITION = (int(GAME_WINDOW_RESOLUTION[0] * config["car"]["position"][0]),
                int(GAME_WINDOW_RESOLUTION[1] * config["car"]["position"][1]))

STAT_FONT = pygame.font.SysFont(config["stats"]["font"]["type"],
                                int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["font"]["size"]))
DIST_FONT = pygame.font.SysFont(config["stats"]["font"]["type"],
                                int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["font"]["dist_size"]))

config["stats"]["global"]["position"][1] = int(config["stats"]["global"]["position"][1] * MAIN_WINDOW_RESOLUTION[1])
config["stats"]["gap"] = int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["font"]["size"] * config["stats"]["gap"])

config["stats"]["best_car"]["img"]["scale"] = config["stats"]["best_car"]["img"]["scale"] * CAR_SIZE
config["stats"]["best_car"]["img"]["position"] = \
    (int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["best_car"]["img"]["position"][0]),
     int(MAIN_WINDOW_RESOLUTION[1] * config["stats"]["best_car"]["img"]["position"][1]))

RED_COLOR = (255, 0, 0)
LIGHT_RED_COLOR = (100, 0, 0)
GREEN_COLOR = (0, 255, 0)
LIGHT_GREEN_COLOR = (0, 100, 0)

SHOW_FRAME_TIME = config["main"]["show_times"]
SHOW_RADAR_LINES = config["main"]["show_radar"]

max_score = 0
gen_num = 0


def timer(func):
    import time

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print(f"Function: {func.__name__}")
        print(f"--- {float(time.time() - start_time) * 1000} milliseconds--- \n")
        return result

    if SHOW_FRAME_TIME:
        return wrapper
    return func


def save():
    with open("results.txt", "a+") as results_file:
        results_file.write(f"Date: {datetime.datetime.now().ctime()} \n")
        results_file.write(f"Generations: {gen_num}\n")
        results_file.write(f"Max score: {max_score}\n")
        results_file.write(f"\n")


def blit_rotate_center(surface, image, topleft, angle):
    """
    Rotate a surface and blit it to the window
    :param topleft: the top left position of the image
    :param surface: the surface to blit to
    :param image: the image surface to rotate
    :param angle: a float value for angle
    :return: None
    """
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft=topleft).center)

    surface.blit(rotated_image, new_rect.topleft)


class Car:
    IMGS = CAR_IMGS
    MAX_VEL = 5

    def __init__(self, x, y):
        self.img = choice(self.IMGS)

        self.x = x
        self.y = y
        self.rx = x + self.img.get_width() // 2
        self.ry = y + self.img.get_height() // 2

        self.distances = [0 for i in range(9)]

        self.vel = 0
        self.thrust = 0.15
        self.friction = 0.05
        self.tilt_speed = 5

        self.angle = 0

        self.right_top_x = self.x + self.img.get_width()
        self.right_top_y = self.y

        self.score = 0

    def calc_x_y(self, x, y, dist, angle):
        x = int(x + math.cos(math.radians(angle)) * dist)
        y = int(y - math.sin(math.radians(angle)) * dist)
        return x, y

    def move(self):
        self.slow_down()

        global max_score
        self.score += int(self.vel)
        if self.score > max_score:
            max_score = self.score
        self.x, self.y = self.calc_x_y(self.x, self.y, self.vel, self.angle)
        self.rx, self.ry = self.x + self.img.get_width() // 2, self.y + self.img.get_height() // 2

    def slow_down(self):
        if self.vel > 0:
            self.vel -= self.friction
        elif self.vel < 0:
            self.vel = 0

    def speed_up(self):
        if self.vel < self.MAX_VEL:
            self.vel += self.thrust

    def turn_right(self):
        if self.vel > 0:
            self.angle -= self.tilt_speed

    def turn_left(self):
        if self.vel > 0:
            self.angle += self.tilt_speed

    def find_distance(self, border, angle):
        cnt = 0
        while cnt < RADAR_MAX_LEN:
            x, y = self.calc_x_y(self.rx, self.ry, cnt, angle)

            if y < 1:
                y = 1
            pixel = border.img.get_at((x, y))
            if pixel[0] == TRANSPARENT_PIXEL["R"] and pixel[1] == TRANSPARENT_PIXEL["G"] \
                    and pixel[2] == TRANSPARENT_PIXEL["B"] and pixel[3] == TRANSPARENT_PIXEL["A"]:
                cnt += 1
            else:
                break
        return cnt

    def draw(self, window):
        blit_rotate_center(window, self.img, (self.x, self.y), self.angle)

        if SHOW_RADAR_LINES:

            for i in range(len(self.distances)):
                pygame.draw.line(window, RED_COLOR,
                                 self.calc_x_y(self.rx, self.ry, self.distances[i], self.angle + RADAR_ANGLES[i]),
                                 (self.rx, self.ry), RADAR_BEAM_THICKNESS)

    def locate(self, border):
        for i in range(len(self.distances)):
            self.distances[i] = self.find_distance(border, self.angle + RADAR_ANGLES[i])

        return self.distances

    def get_mask(self):
        return pygame.mask.from_surface(self.img)


class Border:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.img = BG_IMG

    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def collide(self, car):
        car_mask = car.get_mask()
        border_mask = pygame.mask.from_surface(self.img)
        offset = (self.x - car.x, self.y - round(car.y))

        point = car_mask.overlap(border_mask, offset)

        if point:
            return True
        return False


class Button:
    def __init__(self, position, size, text=''):
        self.x = position[0]
        self.y = position[1]
        self.width = size[0]
        self.height = size[1]
        self.text = text
        self.color = None
        self.restore_color()

    def restore_color(self):
        if SHOW_RADAR_LINES:
            self.color = GREEN_COLOR
        else:
            self.color = RED_COLOR

    def switch(self):
        global SHOW_RADAR_LINES
        SHOW_RADAR_LINES = not SHOW_RADAR_LINES

        self.restore_color()

    def draw(self, win, outline=None):
        # Call this method to draw the button on the screen
        if outline:
            pygame.draw.rect(win, outline, (self.x - 2, self.y - 2, self.width + 4, self.height + 4), 0)

        pygame.draw.rect(win, self.color, (self.x, self.y, self.width, self.height), 0)

        if self.text != '':
            font = pygame.font.SysFont(config["stats"]["font"]["type"],
                                       int(config["stats"]["font"]["button"] * MAIN_WINDOW_RESOLUTION[0]))
            text = font.render(self.text, 1, (0, 0, 0))
            win.blit(text, (int(self.x + (self.width / 2 - text.get_width() / 2)),
                            int(self.y + (self.height / 2 - text.get_height() / 2))))

    def is_over(self, pos):
        if self.color == RED_COLOR:
            self.color = (100, 0, 0)
        elif self.color == GREEN_COLOR:
            self.color = (0, 100, 0)

        # Pos is the mouse position or a tuple of (x,y) coordinates
        if self.x < pos[0] < self.x + self.width:
            if self.y < pos[1] < self.y + self.height:
                return True

        return False


def get_best_car(cars):
    best_car_data = {"score": -1000,
                     "img": CAR_IMGS[0],
                     "speed": 0,
                     "distances": [0 for i in range(len(config["radar"]["angles"]))],
                     "max_speed": 0
                     }
    for car in cars:
        if car.score > best_car_data["score"]:
            best_car_data = {"score": car.score,
                             "img": car.img,
                             "speed": car.vel,
                             "distances": car.distances,
                             "max_speed": car.MAX_VEL
                             }
    return best_car_data


def font_render(window, font, data, color, position):
    text = font.render(data, 1, color)
    window.blit(text, position)


def draw_in_circle(window, objects, center, radius):
    positions = [
        center[0] - radius,
        center[0] - radius / 4 * 3.6,
        center[0] - radius / 4 * 2.7,
        center[0] - radius / 4 * 1.4,
        center[0],
        center[0] + radius / 4 * 1.4,
        center[0] + radius / 4 * 2.7,
        center[0] + radius / 4 * 3.6,
        center[0] + radius
    ]
    for i, x in enumerate(positions):
        pos = (round(x),
               MAIN_WINDOW_RESOLUTION[1] - round(center[1] + math.sqrt(radius ** 2 - (x - center[0]) ** 2)))

        blit_rotate_center(window, objects[i], pos, config["radar"]["angles"][i])


def draw(main_window, game_window, clock, border, cars, num_alive, draw_lines_switch):
    main_window.blit(MAIN_BG_IMG, (0, 0))
    main_window.blit(game_window, (MAIN_WINDOW_RESOLUTION[0] - GAME_WINDOW_RESOLUTION[0], 0))
    game_window.blit(TRACK, TRACK_POSITION)
    border.draw(game_window)
    draw_lines_switch.draw(main_window)

    font_render(main_window, STAT_FONT, f"fps: {int(clock.get_fps())}", RED_COLOR,
                position=(int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["fps_counter"]["position"][0]),
                          int(MAIN_WINDOW_RESOLUTION[1] * config["stats"]["fps_counter"]["position"][1])))

    for i, car in enumerate(cars):
        car.draw(game_window)

    best_car_data = get_best_car(cars)

    best_car_sector = [
        "_____Best car_____",
        f"Score: {best_car_data['score']}",
        "Img:",
        f"Speed: {round(best_car_data['speed'], 2)}",
        "Distances:"
    ]
    for i, text in enumerate(best_car_sector):
        pos = (config["stats"]["best_car"]["position"][0],
               config["stats"]["best_car"]["position"][1] + i * config["stats"]["gap"])
        font_render(main_window, STAT_FONT, text, RED_COLOR, pos)

    best_car_data['img'] = \
        pygame.transform.scale(best_car_data['img'],
                               (int(CAR_INITIAL_SIZE[0] * config["stats"]["best_car"]["img"]["scale"]),
                                int(CAR_INITIAL_SIZE[1] * config["stats"]["best_car"]["img"]["scale"])))

    pos = (config["stats"]["best_car"]["img"]["position"][0],
           config["stats"]["best_car"]["img"]["position"][1] - best_car_data['img'].get_height() // 2)
    main_window.blit(best_car_data['img'], pos)

    radius = MAIN_WINDOW_RESOLUTION[0] * config["radar"]["arrow"]["positions"]["imgs"]["radius"]
    draw_in_circle(main_window,
                   objects=[ARROW_IMG for i in range(9)],
                   center=(config["radar"]["arrow"]["positions"]["imgs"]["init"][0] * MAIN_WINDOW_RESOLUTION[0],
                           config["radar"]["arrow"]["positions"]["imgs"]["init"][1] * MAIN_WINDOW_RESOLUTION[1]),
                   radius=radius)

    draw_in_circle(main_window,
                   objects=[DIST_FONT.render(str(best_car_data["distances"][i]), 1, RED_COLOR)
                            for i in range(len(best_car_data["distances"]))],
                   center=(config["radar"]["arrow"]["positions"]["text"]["init"][0] * MAIN_WINDOW_RESOLUTION[0],
                           config["radar"]["arrow"]["positions"]["text"]["init"][1] * MAIN_WINDOW_RESOLUTION[1]),
                   radius=radius * config["radar"]["arrow"]["positions"]["text"]["radius"])

    global_stats_sector = [
        "_____Global stats_____",
        f"Max Score: {max_score}",
        f"Alive: {num_alive}",
        f"Generation: {gen_num}"
    ]
    for i, text in enumerate(global_stats_sector):
        pos = (config["stats"]["global"]["position"][0],
               config["stats"]["global"]["position"][1] + i * config["stats"]["gap"])
        font_render(main_window, STAT_FONT, text, RED_COLOR, pos)


def process_car(car, cars, gens, nets, border, i, counter):
    car.move()

    if car.vel > 0.5:
        gens[i].fitness += car.vel // 5

    data = list(car.locate(border))
    output = nets[i].activate(data)

    if output[0] > 0.5:
        car.speed_up()
    if output[1] > 0.5:
        car.turn_left()
    if output[2] > 0.5:
        car.turn_right()

    if border.collide(car):
        gens[i].fitness -= 1
        cars.pop(i)
        nets.pop(i)
        gens.pop(i)
    if counter > 150:
        if car.vel <= 1:
            gens[i].fitness -= 1
            cars.pop(i)
            nets.pop(i)
            gens.pop(i)
    if car.score >= 50000:
        cars.pop(i)
        nets.pop(i)
        gens.pop(i)


@timer
def process_all_cars(cars, gens, nets, border, counter):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for i, car in enumerate(cars):
            executor.submit(process_car, car, cars, gens, nets, border, i, counter)


def main(genomes, neat_config):
    global gen_num

    counter = 0

    nets = []
    gens = []
    cars = []

    border = Border(BG_POSITION[0], BG_POSITION[1])

    # get the genomes
    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, neat_config)
        nets.append(net)
        car = Car(CAR_POSITION[0], CAR_POSITION[1])
        cars.append(car)
        g.fitness = 0
        gens.append(g)

    draw_lines_switch = Button(position=(int(config["radar"]["button"]["position"][0] * MAIN_WINDOW_RESOLUTION[0]),
                                         config["radar"]["button"]["position"][1]),
                               size=(int(config["radar"]["button"]["size"][0] * MAIN_WINDOW_RESOLUTION[0]),
                                     int(config["radar"]["button"]["size"][1] * MAIN_WINDOW_RESOLUTION[1])),
                               text="drw lns")

    game_window = pygame.Surface(GAME_WINDOW_RESOLUTION)
    main_window = pygame.display.set_mode(MAIN_WINDOW_RESOLUTION)
    clock = pygame.time.Clock()
    pygame.display.set_caption("AI learning to ride")

    while True:
        clock.tick(FRAME_RATE)
        counter += 1

        num_alive = len(cars)

        for event in pygame.event.get():
            mouse_pos = pygame.mouse.get_pos()
            if event.type == pygame.QUIT:
                save()
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    for i, car in enumerate(cars):
                        gens[i].fitness -= 1
                        cars.pop(i)
                        nets.pop(i)
                        gens.pop(i)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if draw_lines_switch.is_over(mouse_pos):
                    draw_lines_switch.switch()
            if not draw_lines_switch.is_over(mouse_pos):
                draw_lines_switch.restore_color()

        if len(cars) == 0:
            break

        process_all_cars(cars, gens, nets, border, counter)

        draw(main_window, game_window, clock, border, cars, num_alive, draw_lines_switch)
        pygame.display.update()
    gen_num += 1


def run(config_file_path):
    """
    Main function for NEAT-NN
    :param config_file_path: path to a config file
    :return: None
    """
    neat_config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                     neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                     config_file_path)

    population = neat.Population(neat_config)
    population.add_reporter(neat.StdOutReporter(True))
    statistics = neat.StatisticsReporter()
    population.add_reporter(statistics)

    try:
        winner = population.run(main, 100)
        print(winner)
    except pygame.error as e:
        pass
    save()


if __name__ == '__main__':
    # get the path to a config file
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config-feedforward.txt")
    # run the NN and th game
    run(config_path)
