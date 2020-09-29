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
    main_config_data = json.load(main_config)

TRANSPARENT_PIXEL = main_config_data["transparent_pixel"]

GAME_WINDOW_RESOLUTION = main_config_data["resolutions"]["game_window"]
MAIN_WINDOW_RESOLUTION = [GAME_WINDOW_RESOLUTION[0] + main_config_data["resolutions"]["main_window"][0],
                          GAME_WINDOW_RESOLUTION[1] + main_config_data["resolutions"]["main_window"][1]]

FRAME_RATE = main_config_data["frame_rate"]

IMG_SRC_FOLDER = main_config_data["imgs"]["img_src_folder"]

CAR_INITIAL_SIZE = main_config_data["imgs"]["car_init_size"]
CAR_SIZE = main_config_data["imgs"]["car_size"]
CAR_IMGS = []
for car_i in range(1, main_config_data["imgs"]["num"]):
    CAR_IMGS.append(pygame.transform.scale(pygame.image.load(os.path.join(
        IMG_SRC_FOLDER, main_config_data["imgs"]["file_names"]["car"].format(car_i))),
        (int(CAR_INITIAL_SIZE[0] * CAR_SIZE), int(CAR_INITIAL_SIZE[1] * CAR_SIZE))))

BG_IMG = pygame.transform.scale2x(pygame.image.load(os.path.join(
    IMG_SRC_FOLDER, main_config_data["imgs"]["file_names"]["surroundings"])))

MAIN_BG_IMG = pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER,
                                                                    main_config_data["imgs"]["file_names"]["main_bg"])),
                                     GAME_WINDOW_RESOLUTION)
TRACK = pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_SRC_FOLDER,
                                                                main_config_data["imgs"]["file_names"]["track"])))

ARROWS = [
    pygame.transform.scale(pygame.image.load(
        os.path.join(IMG_SRC_FOLDER, main_config_data["imgs"]["file_names"]["arrow_left"])),
        main_config_data["imgs"]["arrow_size"]),
    pygame.transform.scale(pygame.image.load(
        os.path.join(IMG_SRC_FOLDER, main_config_data["imgs"]["file_names"]["arrow_left_corner"])),
        main_config_data["imgs"]["arrow_size"]),
    pygame.transform.scale(pygame.image.load(
        os.path.join(IMG_SRC_FOLDER, main_config_data["imgs"]["file_names"]["arrow_forward"])),
        main_config_data["imgs"]["arrow_size"]),
    pygame.transform.scale(pygame.image.load(
        os.path.join(IMG_SRC_FOLDER, main_config_data["imgs"]["file_names"]["arrow_right_corner"])),
        main_config_data["imgs"]["arrow_size"]),
    pygame.transform.scale(pygame.image.load(
        os.path.join(IMG_SRC_FOLDER, main_config_data["imgs"]["file_names"]["arrow_right"])),
        main_config_data["imgs"]["arrow_size"])
]


RADAR_ANGLES = main_config_data["radar"]["angles"]
RADAR_MAX_LEN = main_config_data["radar"]["max_len"]
RADAR_BEAM_THICKNESS = main_config_data["radar"]["beam_thickness"]

BG_POSITION = main_config_data["positions"]["background"]
TRACK_POSITION = main_config_data["positions"]["track"]
CAR_POSITION = main_config_data["positions"]["car"]

STAT_FONT = pygame.font.SysFont(main_config_data["font"]["type"], main_config_data["font"]["size"])
DIST_FONT = pygame.font.SysFont(main_config_data["font"]["type"], main_config_data["font"]["dist_size"])
RED_COLOR = (255, 0, 0)

TEXT_MAP = main_config_data["positions"]["text_map"]

max_score = 0
gen_num = 0


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

        self.dist_forward = 0
        self.dist_left_corner = 0
        self.dist_right_corner = 0
        self.dist_left = 0
        self.dist_right = 0

        self.vel = 0
        self.thrust = 0.15
        self.break_t = 0.15
        self.friction = 0.05
        self.tilt_speed = 4.5

        self.angle = 0

        self.right_top_x = self.x + self.img.get_width()
        self.right_top_y = self.y

        self.moving = False

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

    def speed_break(self):
        if self.vel >= 0 + self.break_t:
            self.vel -= self.break_t

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
            try:
                pixel = border.img.get_at((x, y))
            except:
                if y < 1:
                    y = 1
                pixel = border.img.get_at((x, y))
            if pixel[0] == TRANSPARENT_PIXEL["R"] and pixel[1] == TRANSPARENT_PIXEL["G"]\
                    and pixel[2] == TRANSPARENT_PIXEL["B"] and pixel[3] == TRANSPARENT_PIXEL["A"]:
                cnt += 1
            else:
                break
        return cnt

    def draw(self, window):
        blit_rotate_center(window, self.img, (self.x, self.y), self.angle)

        x, y = self.calc_x_y(self.rx, self.ry, self.dist_forward, self.angle + RADAR_ANGLES["forward"])
        pygame.draw.line(window, RED_COLOR, (x, y), (self.rx, self.ry), RADAR_BEAM_THICKNESS)

        x, y = self.calc_x_y(self.rx, self.ry, self.dist_left_corner, self.angle + RADAR_ANGLES["left_corner"])
        pygame.draw.line(window, RED_COLOR, (x, y), (self.rx, self.ry), RADAR_BEAM_THICKNESS)

        x, y = self.calc_x_y(self.rx, self.ry, self.dist_right_corner, self.angle + RADAR_ANGLES["right_corner"])
        pygame.draw.line(window, RED_COLOR, (x, y), (self.rx, self.ry), RADAR_BEAM_THICKNESS)

        x, y = self.calc_x_y(self.rx, self.ry, self.dist_left, self.angle + RADAR_ANGLES["left"])
        pygame.draw.line(window, RED_COLOR, (x, y), (self.rx, self.ry), RADAR_BEAM_THICKNESS)

        x, y = self.calc_x_y(self.rx, self.ry, self.dist_right, self.angle + RADAR_ANGLES["right"])
        pygame.draw.line(window, RED_COLOR, (x, y), (self.rx, self.ry), RADAR_BEAM_THICKNESS)

    def locate(self, border):
        self.dist_forward = self.find_distance(border, self.angle + RADAR_ANGLES["forward"])
        self.dist_left_corner = self.find_distance(border, self.angle + RADAR_ANGLES["left_corner"])
        self.dist_right_corner = self.find_distance(border, self.angle + RADAR_ANGLES["right_corner"])
        self.dist_left = self.find_distance(border, self.angle + RADAR_ANGLES["left"])
        self.dist_right = self.find_distance(border, self.angle + RADAR_ANGLES["right"])

        return self.dist_forward, self.dist_left_corner, self.dist_right_corner, self.dist_left, self.dist_right

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


def get_best_car(cars):
    best_car_data = {"score": -1000,
                     "img": CAR_IMGS[0],
                     "speed": 0,
                     "distances": [0, 0, 0, 0, 0],
                     "max_speed": 0
                     }
    for car in cars:
        if car.score > best_car_data["score"]:
            best_car_data = {"score": car.score,
                             "img": car.img,
                             "speed": car.vel,
                             "distances":
                                 [
                                     car.dist_left,
                                     car.dist_left_corner,
                                     car.dist_forward,
                                     car.dist_right_corner,
                                     car.dist_right
                                 ],
                             "max_speed": car.MAX_VEL
                             }
    return best_car_data


def font_render(window, font, data, color, position):
    text = font.render(data, 1, color)
    window.blit(text, position)


def draw(main_window, game_window, border, cars, num_alive):
    main_window.blit(MAIN_BG_IMG, (0, 0))
    main_window.blit(game_window, (MAIN_WINDOW_RESOLUTION[0] - GAME_WINDOW_RESOLUTION[0], 0))
    game_window.blit(TRACK, TRACK_POSITION)
    border.draw(game_window)

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
        pos = (TEXT_MAP["best_car_sector"][0], TEXT_MAP["best_car_sector"][1] + i * TEXT_MAP["gap"])
        font_render(main_window, STAT_FONT, text, RED_COLOR, pos)

    best_car_data['img'] = pygame.transform.scale(best_car_data['img'],
                                                  (int(CAR_INITIAL_SIZE[0] * TEXT_MAP["best_car_img_scale"]),
                                                   int(CAR_INITIAL_SIZE[1] * TEXT_MAP["best_car_img_scale"])))
    pos = (TEXT_MAP["best_car_sector"][0] + 90,
           TEXT_MAP["best_car_sector"][1] + 2 * TEXT_MAP["gap"] - best_car_data['img'].get_height() // 2 + 15)
    main_window.blit(best_car_data['img'], pos)

    for i, arrow in enumerate(ARROWS):
        pos = (TEXT_MAP["arrows"]["imgs"]["init"][0] + i * TEXT_MAP["arrows"]["imgs"]["gap"],
               TEXT_MAP["arrows"]["imgs"]["init"][1])
        main_window.blit(arrow, pos)

    for i, dist in enumerate(best_car_data["distances"]):
        pos = (TEXT_MAP["arrows"]["text"]["init"][0] + i * TEXT_MAP["arrows"]["imgs"]["gap"],
               TEXT_MAP["arrows"]["text"]["init"][1])
        font_render(main_window, DIST_FONT, str(dist), RED_COLOR, pos)

    global_stats_sector = [
        "_____Global stats_____",
        f"Max Score: {max_score}",
        f"Alive: {num_alive}",
        f"Generation: {gen_num}"
    ]
    for i, text in enumerate(global_stats_sector):
        pos = (TEXT_MAP["global_stats_sector"][0], TEXT_MAP["global_stats_sector"][1] + i * TEXT_MAP["gap"])
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
    if counter > 200:
        if car.vel <= 2:
            gens[i].fitness -= 1
            cars.pop(i)
            nets.pop(i)
            gens.pop(i)
    if car.score >= 30000:
        cars.pop(i)
        nets.pop(i)
        gens.pop(i)


def main(genomes, config):
    global gen_num

    counter = 0

    nets = []
    gens = []
    cars = []

    border = Border(BG_POSITION[0], BG_POSITION[1])

    # get the genomes
    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        car = Car(CAR_POSITION[0], CAR_POSITION[1])
        cars.append(car)
        g.fitness = 0
        gens.append(g)

    game_window = pygame.Surface(GAME_WINDOW_RESOLUTION)
    main_window = pygame.display.set_mode(MAIN_WINDOW_RESOLUTION)
    clock = pygame.time.Clock()

    while True:
        clock.tick(FRAME_RATE)
        counter += 1

        num_alive = len(cars)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save()
                pygame.quit()
                exit()

        if len(cars) == 0:
            break

        import time
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for i, car in enumerate(cars):
                executor.submit(process_car, car, cars, gens, nets, border, i, counter)

        # old way
        #
        # for i, car in enumerate(cars):
        #     process_car(car, cars, gens, nets, border, i, counter)

        print(f"--- {float(time.time() - start_time) * 1000} milliseconds---")

        draw(main_window, game_window, border, cars, num_alive)
        pygame.display.update()
    gen_num += 1


def run(config_file_path):
    """
    Main function for NEAT-NN
    :param config_file_path: path to a config file
    :return: None
    """
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_file_path)

    population = neat.Population(config)
    population.add_reporter(neat.StdOutReporter(True))
    statistics = neat.StatisticsReporter()
    population.add_reporter(statistics)

    try:
        winner = population.run(main, 100)
    except pygame.error as e:
        pass
    save()


if __name__ == '__main__':
    # get the path to a config file
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config-feedforward.txt")
    # run the NN and th game
    run(config_path)
