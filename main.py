import datetime

import math
import neat
import pygame
from random import choice
import os

pygame.init()

TRANSPARENT_PIXEL = {
    "R": 255,
    "G": 255,
    "B": 255,
    "A": 0
}

GAME_WINDOW_RESOLUTION = (1518, 778)
MAIN_WINDOW_RESOLUTION = (2000, 778)

FRAME_RATE = 30

IMG_SRC_FOLDER = "imgs"

CAR_INITIAL_SIZE = (200, 100)
CAR_SIZE = 0.2
CAR_IMGS = []
for car_i in range(1, 7):
    CAR_IMGS.append(pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER, f"car_{car_i}.png")),
                                           (int(CAR_INITIAL_SIZE[0] * CAR_SIZE), int(CAR_INITIAL_SIZE[1] * CAR_SIZE))))

BG_IMG = pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_SRC_FOLDER, "surroundings.png")))
MAIN_BG_IMG = pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER, "main_bg.jpg")),
                                     GAME_WINDOW_RESOLUTION)
TRACK = pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_SRC_FOLDER, "track.png")))
RADAR = pygame.image.load(os.path.join(IMG_SRC_FOLDER, "radar.png"))
RADAR_ANGLES = {
    "forward": 0,
    "left_corner": 45,
    "right_corner": -45,
    "left": 90,
    "right": -90
}

BG_POSITION = (0, 0)
TRACK_POSITION = (-20, -11)
CAR_POSITION = (700, 190)

STAT_FONT = pygame.font.SysFont("comicsans", 50)
RED_COLOR = (255, 0, 0)
TEXT_MAP = {
    "best_car_sector": (10, 10),
    "best_car_score": (10, 70),
    "best_car_img_text": (10, 130),
    "best_car_img": (100, 110),
    "best_car_speed": (10, 190),

    "global_stats_sector": (10, 400),
    "max_score": (10, 460),
    "alive": (10, 510),
    "generation": (10, 560)
}

max_score = 0
gen_num = 1


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

        self.vel = 0
        self.thrust = 0.15
        self.friction = 0.05
        self.tilt_speed = 4

        self.angle = 0

        self.right_top_x = self.x + self.img.get_width()
        self.right_top_y = self.y

        self.moving = False

        self.score = 0

    def calc_x_y(self, dist):
        real_angle = self.angle

        if real_angle == 90:
            y = int(self.y - dist)
            x = self.x
        else:
            x = int(self.x + math.cos(math.radians(real_angle)) * dist)
            y = int(self.y - math.sin(math.radians(real_angle)) * dist)
        return x, y

    def move(self):
        self.slow_down()

        global max_score
        self.score += int(self.vel)
        if self.score > max_score:
            max_score = self.score
        self.x, self.y = self.calc_x_y(self.vel)

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

    def draw(self, window):
        blit_rotate_center(window, self.img, (self.x, self.y), self.angle)

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


class Radar:
    def __init__(self, car):
        self.x = car.x + car.img.get_width() // 2
        self.y = car.y + car.img.get_height() // 2

    def calc_x_y(self, dist, angle):
        if angle == 90:
            y = int(self.y - dist)
            x = self.x
        else:
            x = int(self.x + math.cos(math.radians(angle)) * dist)
            y = int(self.y - math.sin(math.radians(angle)) * dist)
        return x, y

    def move(self, car):
        self.x, self.y = self.calc_x_y(car.vel, car.angle)

    def find_distance(self, border, angle):
        cnt = 0
        while cnt < 200:
            x, y = self.calc_x_y(cnt, angle)
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

    def draw(self, game_window, car, border):
        dist_forward = self.find_distance(border, car.angle + RADAR_ANGLES["forward"])
        dist_left_corner = self.find_distance(border, car.angle + RADAR_ANGLES["left_corner"])
        dist_right_corner = self.find_distance(border, car.angle + RADAR_ANGLES["right_corner"])
        dist_left = self.find_distance(border, car.angle + RADAR_ANGLES["left"])
        dist_right = self.find_distance(border, car.angle + RADAR_ANGLES["right"])

        thickness = 3

        x, y = self.calc_x_y(dist_forward, car.angle + RADAR_ANGLES["forward"])
        pygame.draw.line(game_window, RED_COLOR, (x, y), (self.x, self.y), thickness)

        x, y = self.calc_x_y(dist_left_corner, car.angle + RADAR_ANGLES["left_corner"])
        pygame.draw.line(game_window, RED_COLOR, (x, y), (self.x, self.y), thickness)

        x, y = self.calc_x_y(dist_right_corner, car.angle + RADAR_ANGLES["right_corner"])
        pygame.draw.line(game_window, RED_COLOR, (x, y), (self.x, self.y), thickness)

        x, y = self.calc_x_y(dist_left, car.angle + RADAR_ANGLES["left"])
        pygame.draw.line(game_window, RED_COLOR, (x, y), (self.x, self.y), thickness)

        x, y = self.calc_x_y(dist_right, RADAR_ANGLES["right"])
        pygame.draw.line(game_window, RED_COLOR, (x, y), (self.x, self.y), thickness)

    def locate(self, car, border):
        dist_forward = self.find_distance(border, car.angle + RADAR_ANGLES["forward"])
        dist_left_corner = self.find_distance(border, car.angle + RADAR_ANGLES["left_corner"])
        dist_right_corner = self.find_distance(border, RADAR_ANGLES["right_corner"])
        dist_left = self.find_distance(border, RADAR_ANGLES["left"])
        dist_right = self.find_distance(border, RADAR_ANGLES["right"])

        return dist_forward, dist_left_corner, dist_right_corner, dist_left, dist_right


def get_best_car(cars):
    best_car_data = {"score": -1000, "img": RADAR, "speed": 0}
    for car in cars:
        if car.score > best_car_data["score"]:
            best_car_data = {"score": car.score, "img": car.img, "speed": car.vel}
    return best_car_data


def draw(main_window, game_window, border, cars, radars, num_alive):
    main_window.blit(MAIN_BG_IMG, (0, 0))
    main_window.blit(game_window, (MAIN_WINDOW_RESOLUTION[0] - GAME_WINDOW_RESOLUTION[0], 0))
    game_window.blit(TRACK, TRACK_POSITION)
    border.draw(game_window)

    for i, car in enumerate(cars):
        car.draw(game_window)
        radars[i].draw(game_window, car, border)

    best_car_data = get_best_car(cars)
    text = STAT_FONT.render("_____Best car_____", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["best_car_sector"])

    text = STAT_FONT.render(f"Score: {best_car_data['score']}", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["best_car_score"])
    text = STAT_FONT.render("Img:", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["best_car_img_text"])
    best_car_data['img'] = pygame.transform.scale(best_car_data['img'],
                                                  (int(CAR_INITIAL_SIZE[0] * 0.7), int(CAR_INITIAL_SIZE[1] * 0.7)))
    main_window.blit(best_car_data['img'], TEXT_MAP["best_car_img"])
    text = STAT_FONT.render(f"Speed: {round(best_car_data['speed'], 2)}", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["best_car_speed"])

    text = STAT_FONT.render("_____Global stats_____", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["global_stats_sector"])
    text = STAT_FONT.render(f"Max Score: {max_score}", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["max_score"])
    text = STAT_FONT.render(f"Alive: {num_alive}", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["alive"])
    text = STAT_FONT.render(f"Generation: {gen_num}", 1, RED_COLOR)
    main_window.blit(text, TEXT_MAP["generation"])


def main(genomes, config):
    global gen_num

    counter = 0

    nets = []
    gens = []
    cars = []
    radars = []

    border = Border(BG_POSITION[0], BG_POSITION[1])

    # get the genomes
    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        car = Car(CAR_POSITION[0], CAR_POSITION[1])
        cars.append(car)
        radars.append(Radar(car))
        g.fitness = 0
        gens.append(g)

    num_alive = len(cars)

    game_window = pygame.Surface(GAME_WINDOW_RESOLUTION)
    main_window = pygame.display.set_mode(MAIN_WINDOW_RESOLUTION)
    clock = pygame.time.Clock()

    while True:
        clock.tick(FRAME_RATE)
        counter += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

        if len(cars) == 0:
            break

        for i, car in enumerate(cars):
            car.move()
            radars[i].move(car)

            if car.score % 2000 == 0:
                car.MAX_VEL += 0.1

            if car.vel > 0.5:
                gens[i].fitness += car.vel // 5

            data = radars[i].locate(car, border)
            output = nets[i].activate(data)

            if output[0] > 0.5:
                car.speed_up()
            if output[1] > 0.5:
                car.turn_left()
            if output[2] > 0.5:
                car.turn_right()

        # keys = pygame.key.get_pressed()
        # if keys[pygame.K_w]:
        #     cars[1].speed_up()
        # if keys[pygame.K_d]:
        #     cars[1].turn_right()
        # if keys[pygame.K_a]:
        #     cars[1].turn_left()

        for i, car in enumerate(cars):
            if border.collide(car):
                gens[i].fitness -= 1
                cars.pop(i)
                radars.pop(i)
                nets.pop(i)
                gens.pop(i)
            if counter % 60 == 0:
                if car.vel <= 0.5:
                    gens[i].fitness -= 1
                    cars.pop(i)
                    radars.pop(i)
                    nets.pop(i)
                    gens.pop(i)

        draw(main_window, game_window, border, cars, radars, num_alive)
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
    with open("results.txt", "a+") as results_file:
        results_file.write(f"Date: {datetime.datetime.now().ctime()} \n")
        results_file.write(f"Generations: {gen_num}\n")
        results_file.write(f"Max score: {max_score}\n")
        results_file.write(f"\n")


if __name__ == '__main__':
    # get the path to a config file
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config-feedforward.txt")

    # run the NN and th game
    run(config_path)
