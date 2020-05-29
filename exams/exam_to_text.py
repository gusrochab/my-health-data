import copy
import io
import logging
import matplotlib.pyplot as plt
import os
import statistics
import numpy as np
from google.cloud import vision
from PIL import Image
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from .word_box import WordBox


# logging.basicConfig(filename="get_text_from_line.log", level=logging.DEBUG,
#                    format='%(asctime)s:%(levelname)s:%(message)s')


def get_response(img_file):
    """
    :param img_file: Image path
    :return: Response from google Vision API and a image array
    """

    with io.open(img_file, 'rb') as f:
        img_binary = f.read()

    vision_img = vision.types.Image(content=img_binary)
    client = vision.ImageAnnotatorClient()
    response = client.document_text_detection(image=vision_img)
    image = Image.open(img_file)
    img_array = np.array(image)
    return response, img_array


def get_pages(response):
    """
    :return: List with all pages in document
    """

    document = response.full_text_annotation
    pages = []
    for page in document.pages:
        pages.append(page)
    return pages


def get_blocks_vertices(page):
    """
    :return: list of lists wiht the four vertices of the block text element
    """

    blocks_vertices = []
    for block in page.blocks:
        block_vertices = []
        for vertex in block.bounding_box.vertices:
            block_vertices.append((int(vertex.x), int(vertex.y)))
        blocks_vertices.append(block_vertices)
    return blocks_vertices


def get_word_boxes(response):
    """
    :return: list of WordBox objects
    """

    word_boxes = []
    for word_box in response.text_annotations:
        text = word_box.description
        vertices = []
        for vertex in word_box.bounding_poly.vertices:
            vertices.append((int(vertex.x), int(vertex.y)))
        center = get_box_center_point(vertices)
        word_boxes.append(WordBox(text, vertices, center))
    word_boxes.pop(0)
    return word_boxes


def get_box_center_point(word_vetices):
    x = 0
    y = 0
    for vertex in word_vetices[1:]:
        x += vertex[0]
        y += vertex[1]
    x_med = x / len(word_vetices[1:])
    y_med = y / len(word_vetices[1:])
    return (x_med, y_med)


def get_center_lines(img_array, word_boxes):
    """
    :param img_array: Image in array format
    :param word_boxes: list of WordBox objects
    :return: Start and end points for each line in document
    """

    center_lines = []
    for word_box in word_boxes:
        left_point = (int((word_box.vertices[0][0] + word_box.vertices[3][0]) / 2),
                      int((word_box.vertices[0][1] + word_box.vertices[3][1]) / 2))
        right_point = (int((word_box.vertices[1][0] + word_box.vertices[2][0]) / 2),
                       int((word_box.vertices[1][1] + word_box.vertices[2][1]) / 2))
        a, b = get_line_parameters(left_point, right_point)
        max_x = img_array.shape[1]
        # y = ax + b
        initial_point = (0, int(0 * a + b))
        final_point = (max_x, int(max_x * a + b))
        center_lines.append((initial_point, final_point))
    center_lines = list(set(center_lines))
    return center_lines


def get_line_parameters(p1, p2):
    # y = ax + b
    try:
        a = (p2[1] - p1[1]) / (p2[0] - p1[0])
    except ZeroDivisionError:
        a = 0
    b = p1[1] - a * p1[0]
    return (a, b)


def filter_center_lines(img_array, center_lines, slope_filter=0.01, y_filter=10):
    """
    :param img_array: Image in array format
    :param center_lines: List of lines points
    :param slope_filter: aceptable degrees difference between a line slope and the mean line slope
    :param y_filter: distance in pixls between the y(0) of two sequential lines
    """

    a_list = []
    good_slope_center_lines = []
    unique_center_lines = []
    # get the slope mode
    for center_line in center_lines:
        a, _ = get_line_parameters(center_line[0], center_line[1])
        a_list.append(round(a, 3))

    # delete lines with wrong slope
    a_mode = abs(statistics.mode(a_list))
    for i in range(len(center_lines) - 1):
        a = abs(a_list[i])
        if a < a_mode + slope_filter:
            good_slope_center_lines.append(center_lines[i])

    # delete very close lines
    good_slope_center_lines = sorted(good_slope_center_lines)
    y_max = img_array.shape[0]
    for i in range(len(good_slope_center_lines) - 1):
        y = good_slope_center_lines[i][0][1]
        next_y = good_slope_center_lines[i + 1][0][1]
        if abs(y - next_y) > y_filter:
            unique_center_lines.append(good_slope_center_lines[i])
    return unique_center_lines


def get_inspection_points(img_array, center_lines, blocks_vertices, points_per_line):
    """
    Define inspection points along the lines

    :param img_array: Image in array format
    :param center_lines: List of line's points
    :param blocks_vertices: List of block's elements vertices
    :param points_per_line: Number of points to inspect per line
    :return: List of points
    """

    inspection_points = []
    for line in center_lines:
        a, b = get_line_parameters(line[0], line[1])
        x = 0
        final_x = img_array.shape[1]
        inspection_point = []
        while x < final_x:
            y = a * x + b
            for block_vertices in blocks_vertices:
                point = Point(x, y)
                polygon = Polygon(block_vertices)
                if polygon.contains(point):
                    inspection_point.append((int(x), int(y)))
            x += img_array.shape[1] / points_per_line
        inspection_points.append(inspection_point)
    return inspection_points


def get_text_from_lines(inspection_points, word_boxes):
    """
    Evaluate if inspection point is inside of a word box
    :param inspection_points: List of inspection points
    :param word_boxes: list of WordBox objects
    :return: List with text from each line
    """

    wb = copy.deepcopy(word_boxes)
    full_text = []
    for line in inspection_points:
        line_text = ''
        for inspection_point in line:
            point = Point(inspection_point)
            for i in range(len(wb) - 1):
                polygon = Polygon(wb[i].vertices)
                if polygon.contains(point):
                    line_text += wb[i].text
                    line_text += ' '
                    wb.pop(i)
        full_text.append(line_text)
    return full_text


def print_img(img_array, f_size=20):
    fig = plt.figure(figsize=(f_size,f_size))
    plt.imshow(img_array)


def draw_block_boxes(img_array, blocks_vertices, thickness=1):
    for block_vertices in blocks_vertices:
        cv2.rectangle(img_array, pt1=block_vertices[0], pt2=block_vertices[2], color=(0,0,255), thickness=thickness)


def draw_center_lines(img_array, center_lines, thickness=1):
    for center_line in center_lines:
        cv2.line(img_array, pt1=center_line[0], pt2=center_line[1], color=(255,0,0), thickness=thickness)


def draw_inspection_points(img_array, inspection_points, radius=2):
    for line in inspection_points:
        for inspection_point in line:
            cv2.circle(img_array, inspection_point, radius, color=(255,0,0))


def save_img(img_array, img_file):
    file_ext = os.path.splitext(img_file)[1]
    file_out = f'{os.path.splitext(img_file)[0]} - out.{file_ext}'
    cv2.imwrite(file_out, img_array)


def save_file(text_from_lines, img_file):
    file_out = f'{os.path.splitext(img_file)[0]} - out.txt'
    with open(file_out, 'w') as f:
        for line in text_from_lines:
            f.write(str(line))
            f.write('\n')


def get_text(img_file):
    response, img_array = get_response(img_file)
    pages = get_pages(response)

    for page in pages:
        blocks_vertices = get_blocks_vertices(page)
        word_boxes = get_word_boxes(response)
        center_lines = get_center_lines(img_array, word_boxes)
        filtered_center_lines = filter_center_lines(img_array, center_lines)
        inspection_points = get_inspection_points(img_array, filtered_center_lines, blocks_vertices, 100)
        text_from_lines = get_text_from_lines(inspection_points, word_boxes)

        # draw_block_boxes(img_array, blocks_vertices, thickness=1)
        # draw_center_lines(img_array, filtered_center_lines, thickness=1)
        # draw_inspection_points(img_array, inspection_points, radius=2)

        # save_file(text_from_lines, img_file)
        # save_img(img_array, img_file)
        return text_from_lines


def parce_text(text_from_lines):
    pass



