import datetime
import math
import sys
from copy import copy

import neat
import pygame
from random import choice
import os
import json
import concurrent.futures

pygame.init()

# load config from file
with open("main-config.json") as main_config:
    config = json.load(main_config)

TRANSPARENT_PIXEL = config["transparent_pixel"]

# set resolutions
GAME_WINDOW_RESOLUTION = config["main"]["resolutions"]["game_window"]
MAIN_WINDOW_RESOLUTION = [int(val * cf)
                          for val, cf in zip(GAME_WINDOW_RESOLUTION, config["main"]["resolutions"]["main_window"])]

FRAME_RATE = config["main"]["frame_rate"]

IMG_SRC_FOLDER = config["main"]["img_src_folder"]

# get the images
CAR_INITIAL_SIZE = config["car"]["car_init_size"]
CAR_SIZE = MAIN_WINDOW_RESOLUTION[0] * config["car"]["car_size"]
CAR_IMGS = [
    pygame.transform.scale(pygame.image.load(os.path.join(IMG_SRC_FOLDER, config["car"]["img"].format(i + 1))),
                           [int(CAR_INITIAL_SIZE[i] * CAR_SIZE) for i in range(2)])
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
                                   [int(ARROW_INITIAL_SIZE[i] * ARROW_SIZE) for i in range(2)])

# set radar params
RADAR_ANGLES = config["radar"]["angles"]
RADAR_MAX_LEN = config["radar"]["max_len"]
RADAR_BEAM_THICKNESS = config["radar"]["beam_thickness"]

# set image positions
BG_POSITION = config["main"]["imgs"]["position"]
TRACK_POSITION = BG_POSITION
CAR_POSITION = [int(val * cf) for val, cf in zip(GAME_WINDOW_RESOLUTION, config["car"]["position"])]


# set fonts
STAT_FONT = pygame.font.SysFont(config["stats"]["font"]["type"],
                                int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["font"]["size"]))
DIST_FONT = pygame.font.SysFont(config["stats"]["font"]["type"],
                                int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["font"]["dist_size"]))

# set text positions
config["stats"]["global"]["position"][1] = int(config["stats"]["global"]["position"][1] * MAIN_WINDOW_RESOLUTION[1])
config["stats"]["gap"] = int(MAIN_WINDOW_RESOLUTION[0] * config["stats"]["font"]["size"] * config["stats"]["gap"])

config["stats"]["best_car"]["img"]["scale"] = config["stats"]["best_car"]["img"]["scale"] * CAR_SIZE
config["stats"]["best_car"]["img"]["position"] = \
    [int(val * cf) for val, cf in zip(MAIN_WINDOW_RESOLUTION, config["stats"]["best_car"]["img"]["position"])]


# set some colors
BLACK_COLOR = pygame.Color("#000000")
RED_COLOR = pygame.Color("#B90E0A")
LIGHT_RED_COLOR = pygame.Color("#990F02")
GREEN_COLOR = pygame.Color("#3BB143")
LIGHT_GREEN_COLOR = pygame.Color("#0B6623")

SHOW_FRAME_TIME = config["main"]["show_times"]
SHOW_RADAR_LINES = config["main"]["show_radar"]

max_score = 0
gen_num = 0
pop_size = 0


def timer(on=True):
    """
    Simple timer decorator.
        Prints function execution time
    :param on: display time or not
    :return: wrapped function
    """
    def inner_timer(original_function):
        import time

        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = original_function(*args, **kwargs)
            print(f"Function: {original_function.__name__}")
            print(f"--- {float(time.time() - start_time) * 1000} milliseconds--- \n")
            return result

        if on:
            print("executing")
            return wrapper
        return original_function
    return inner_timer


def save():
    """
    Saves simulation info to the results file
    :return: None
    """
    with open("results.txt", "a+") as results_file:
        results_file.write(f"Date: {datetime.datetime.now().ctime()}\n")
        results_file.write(f"Generations: {gen_num}\n")
        results_file.write(f"Pop size: {pop_size}\n")
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
    """
    Represents single car
    """
    IMGS = CAR_IMGS
    MAX_VEL = 5

    def __init__(self, x, y):
        self.img = choice(self.IMGS)

        self.x = x
        self.y = y
        # radar coordinates
        self.rx = x + self.img.get_width() // 2
        self.ry = y + self.img.get_height() // 2

        # initial radar distances
        self.distances = [0 for i in range(9)]

        self.vel = 0
        self.thrust = 0.15
        self.friction = 0.05
        self.tilt_speed = 5
        self.angle = 0

        self.score = 0

    def calc_x_y(self, x, y, dist, angle):
        """
        Calculates new (x, y) using given (x, y) ; distance ; angle
        :param x: initial x coordinate
        :param y: initial y coordinate
        :param dist: distance
        :param angle: angle
        :return: new (x, y)
        """
        x = int(x + math.cos(math.radians(angle)) * dist)
        y = int(y - math.sin(math.radians(angle)) * dist)
        return x, y

    def move(self):
        """
        Moves car using current car velocity and friction
        :return: None
        """
        self.slow_down()

        # increment the score
        global max_score
        self.score += int(self.vel)
        if self.score > max_score:
            max_score = self.score

        # calculate new car (x, y) and radar (x, y)
        self.x, self.y = self.calc_x_y(self.x, self.y, self.vel, self.angle)
        self.rx, self.ry = self.x + self.img.get_width() // 2, self.y + self.img.get_height() // 2

    def slow_down(self):
        """
        Lower car velocity by given car friction
        :return: None
        """
        if self.vel > 0:
            self.vel -= self.friction
        # don't decrease velocity if its lower or equal to 0
        elif self.vel < 0:
            self.vel = 0

    def speed_up(self):
        """
        Increase car velocity by given thrust
        :return: None
        """
        if self.vel < self.MAX_VEL:
            self.vel += self.thrust

    def turn_right(self):
        """
        Turns car right by given tilt speed angle
        :return: None
        """
        # turn car only if its velocity is greater than 0 (if car is moving)
        if self.vel > 0:
            self.angle -= self.tilt_speed

    def turn_left(self):
        """
        Turns car left by given tilt speed angle
        :return: None
        """
        # turn car only if its velocity is greater than 0 (if car is moving)
        if self.vel > 0:
            self.angle += self.tilt_speed

    def find_distance(self, border, angle):
        """
        Finds distance from car to border at given angle.
            It does it by calculating (x, y) coordinates at given angle and different distances from 0 and till
            the pixel at new coordinates wont be transparent (r: 255, g: 255, b: 255, a: 0)
        :param border: border object
        :param angle: radar angle
        :return: distance to the border
        """
        # initial distance
        cnt = 0
        while cnt < RADAR_MAX_LEN:
            x, y = self.calc_x_y(self.rx, self.ry, cnt, angle)

            if y < 1:
                y = 1
            # get new pixel value
            pixel = border.img.get_at((x, y))
            # check, if pixel is transparent
            if pixel[0] == TRANSPARENT_PIXEL["R"] and pixel[1] == TRANSPARENT_PIXEL["G"] \
                    and pixel[2] == TRANSPARENT_PIXEL["B"] and pixel[3] == TRANSPARENT_PIXEL["A"]:
                cnt += 1
            else:
                break
        return cnt

    def draw(self, window):
        """
        Draws the car and also radar lines if SHOW_RADAR_LINES flag is set to True
        :param window:
        :return: None
        """
        # blit the car at given angle
        blit_rotate_center(window, self.img, (self.x, self.y), self.angle)

        # draw radar lines
        if SHOW_RADAR_LINES:
            for i in range(len(self.distances)):
                pygame.draw.line(window, RED_COLOR,
                                 self.calc_x_y(self.rx, self.ry, self.distances[i], self.angle + RADAR_ANGLES[i]),
                                 (self.rx, self.ry), RADAR_BEAM_THICKNESS)

    def locate(self, border):
        """
        Calculates distances from car to the border at given angles (RADAR_ANGLES)
        :param border:
        :return: list with distances
        """
        for i in range(len(self.distances)):
            self.distances[i] = self.find_distance(border, self.angle + RADAR_ANGLES[i])

        return self.distances

    @property
    def mask(self):
        """
        Gets mask object generated using self.img
        :return: pygame.Mask object
        """
        return pygame.mask.from_surface(self.img)


class Border:
    """
    Represents track border
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.img = BG_IMG

    def draw(self, window):
        """
        Draws (blits) border image on a given surface
        :param window: pygame.Surface object
        :return: None
        """
        window.blit(self.img, (self.x, self.y))

    @property
    def mask(self):
        """
        Gets mask object generated using self.img
        :return: pygame.Mask object
        """
        return pygame.mask.from_surface(self.img)

    def collide(self, car):
        """
        Check if the given "car" object collides with Border
        :param car: Car object
        :return: bool
        """
        # get the masks
        car_mask = car.mask
        border_mask = self.mask
        # calculate the offset
        offset = (self.x - car.x, self.y - round(car.y))
        # check for collision point
        return car_mask.overlap(border_mask, offset)


class Button:
    """
    Represents simple button
    """
    def __init__(self, position, size, text=''):
        self.x = position[0]
        self.y = position[1]
        self.width = size[0]
        self.height = size[1]
        self.text = text
        self.color = None
        self.restore_color()

    def restore_color(self):
        """
        Restores button color to default value
        :return: None
        """
        if SHOW_RADAR_LINES:
            self.color = GREEN_COLOR
        else:
            self.color = RED_COLOR

    def switch(self):
        """
        Switches the button (on / off) by changing SHOW_RADAR_LINES flag
        :return: None
        """
        global SHOW_RADAR_LINES
        SHOW_RADAR_LINES = not SHOW_RADAR_LINES

        self.restore_color()

    def draw(self, win, outline_color=None, outline_size=2):
        """
        Draws (blits) the button on a given window
        :param win: pygame.Surface object
        :param outline_color: color of the outline
        :param outline_size: outline thickness
        :return: None
        """

        # draw outline if needed
        if outline_color:
            pygame.draw.rect(win, outline_color, (self.x - outline_size, self.y - outline_size,
                                                  self.width + outline_size * 2, self.height + outline_size * 2), 0)

        pygame.draw.rect(win, self.color, (self.x, self.y, self.width, self.height), 0)

        # draw text if needed (if there is any text)
        if self.text != '':
            font = pygame.font.SysFont(config["stats"]["font"]["type"],
                                       int(config["stats"]["font"]["button"] * MAIN_WINDOW_RESOLUTION[0]))
            text = font.render(self.text, 1, (0, 0, 0))
            win.blit(text, (int(self.x + (self.width / 2 - text.get_width() / 2)),
                            int(self.y + (self.height / 2 - text.get_height() / 2))))

    def is_over(self, pos):
        """
        Checks if mouse cursor is over the button
        :param pos: mouse cursor position
        :return: bool
        """
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
    """
    Gets data about best car (by score)
    :param cars:
    :return: None
    """
    best_car = Car(0, 0)
    for car in cars:
        if car.score > best_car.score:
            best_car = copy(car)
    return best_car


def font_render(window, font, data, color, position):
    """
    Renders given text (data) using given font, color, position
    on a given surface (window)
    :param window: pygame.Surface object
    :param font: pygame.Font object
    :param data: text to render
    :param color: some color
    :param position: (x, y) position to render on
    :return: None
    """
    # create pygame.Rect object with given text
    text = font.render(data, 1, color)
    # draw (blit) the text
    window.blit(text, position)


def draw_in_circle(window, objects, center, radius):
    """
    Draws given objects in circle with given radius on given surface
    :param window: pygame.Surface object
    :param objects: objects to render
    :param center: center of the circle
    :param radius: radius of the circle
    :return: None
    """
    # x positions of the objects
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
    """
    Main "draw" method
    Draws given objects of given surfaces
    :param main_window: main window
    :param game_window: game window
    :param clock: global clock value
    :param border: Border object
    :param cars: list of Car objects
    :param num_alive: num of existing cars
    :param draw_lines_switch: Button object
    :return: None
    """
    main_window.blit(MAIN_BG_IMG, (0, 0))
    main_window.blit(game_window, (MAIN_WINDOW_RESOLUTION[0] - GAME_WINDOW_RESOLUTION[0], 0))
    game_window.blit(TRACK, TRACK_POSITION)
    border.draw(game_window)
    draw_lines_switch.draw(main_window, outline_color=BLACK_COLOR, outline_size=3)

    # render fps counter
    font_render(main_window, STAT_FONT, f"fps: {int(clock.get_fps())}", RED_COLOR,
                position=[int(val * cf)
                          for val, cf in zip(MAIN_WINDOW_RESOLUTION, config["stats"]["fps_counter"]["position"])])

    # render cars
    for i, car in enumerate(cars):
        car.draw(game_window)

    # render all statistics data
    best_car = get_best_car(cars)
    best_car_sector = [
        "_____Best car_____",
        f"Score: {best_car.score}",
        "Img:",
        f"Speed: {round(best_car.vel, 2)}",
        "Distances:"
    ]
    for i, text in enumerate(best_car_sector):
        pos = (config["stats"]["best_car"]["position"][0],
               config["stats"]["best_car"]["position"][1] + i * config["stats"]["gap"])
        font_render(main_window, STAT_FONT, text, RED_COLOR, pos)

    best_car.img = \
        pygame.transform.scale(best_car.img,
                               [int(CAR_INITIAL_SIZE[i] * config["stats"]["best_car"]["img"]["scale"])
                                for i in range(2)])

    pos = (config["stats"]["best_car"]["img"]["position"][0],
           config["stats"]["best_car"]["img"]["position"][1] - best_car.img.get_height() // 2)
    main_window.blit(best_car.img, pos)

    radius = MAIN_WINDOW_RESOLUTION[0] * config["radar"]["arrow"]["positions"]["imgs"]["radius"]
    draw_in_circle(main_window,
                   objects=[ARROW_IMG for i in range(9)],
                   center=[int(val * cf) for val, cf in
                           zip(MAIN_WINDOW_RESOLUTION, config["radar"]["arrow"]["positions"]["imgs"]["init"])],
                   radius=radius)

    draw_in_circle(main_window,
                   objects=[DIST_FONT.render(str(best_car.distances[i]), 1, RED_COLOR)
                            for i in range(len(best_car.distances))],
                   center=[int(val * cf) for val, cf in
                           zip(MAIN_WINDOW_RESOLUTION, config["radar"]["arrow"]["positions"]["text"]["init"])],
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
    """
    Processes single car (moves it, draws it, checks for collision ...)
    :param car: Car object
    :param cars: list of Car objects
    :param gens: genomes
    :param nets: networks
    :param border: Border object
    :param i: index of the car
    :param counter: global clock value
    :return: None
    """
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

    # remove collided cars
    if border.collide(car):
        gens[i].fitness -= 1
        cars.pop(i)
        nets.pop(i)
        gens.pop(i)
    # remove standing cars
    if counter > 150:
        if car.vel <= 1:
            gens[i].fitness -= 1
            cars.pop(i)
            nets.pop(i)
            gens.pop(i)
    # remove car if its too good
    if car.score >= 50000:
        cars.pop(i)
        nets.pop(i)
        gens.pop(i)


@timer(on=SHOW_FRAME_TIME)
def process_all_cars(cars, gens, nets, border, counter):
    """
    Processes all cars
    :param cars: list of Car objects
    :param gens: genomes
    :param nets: networks
    :param border: Border object
    :param counter: global clock value
    :return: None
    """
    # process cars in threads to speed up the process
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for i, car in enumerate(cars):
            executor.submit(process_car, car, cars, gens, nets, border, i, counter)


def main(genomes, neat_config):
    """
    Main program function
    :param genomes: neat-genomes
    :param neat_config: neat-config
    :return: None
    """
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

    # get all the objects
    draw_lines_switch = Button(position=(int(config["radar"]["button"]["position"][0] * MAIN_WINDOW_RESOLUTION[0]),
                                         config["radar"]["button"]["position"][1]),
                               size=[int(val * cf) for val, cf in
                                     zip(MAIN_WINDOW_RESOLUTION, config["radar"]["button"]["size"])],
                               text="drw lns")

    game_window = pygame.Surface(GAME_WINDOW_RESOLUTION)
    main_window = pygame.display.set_mode(MAIN_WINDOW_RESOLUTION)
    clock = pygame.time.Clock()
    pygame.display.set_caption("AI learning to ride")

    # main program loop
    while True:
        clock.tick(FRAME_RATE)
        counter += 1

        num_alive = len(cars)

        # process all the events
        for event in pygame.event.get():
            mouse_pos = pygame.mouse.get_pos()
            # if the window is closed
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # process key presses
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

    global pop_size
    pop_size = neat_config.pop_size

    # create population and add a reporter (logger)
    population = neat.Population(neat_config)
    population.add_reporter(neat.StdOutReporter(True))
    statistics = neat.StatisticsReporter()
    population.add_reporter(statistics)

    try:
        winner = population.run(main, 100)
    except pygame.error as e:
        print(e.__context__)
        print(e.__traceback__)
    else:
        print(winner)
    finally:
        save()


if __name__ == '__main__':
    # get the path to a config file
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config-feedforward.txt")
    # run the NN and th game
    run(config_path)
