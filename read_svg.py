#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr  7 19:12:59 2023

@author: darrenlynch
"""
    
import xmltodict
import numpy as np

def get_view_box(svg_dict):
    view_box_string = svg_dict['svg']['@viewBox']
    view_box_list = view_box_string.split(' ')
    return view_box_list

def get_width_height(svg_dict):
    width_height_string = [svg_dict['svg']['@width'], svg_dict['svg']['@height']]
    return width_height_string

def remove_at_keys(d):
    if isinstance(d, dict):
        return {k: remove_at_keys(v) for k, v in d.items() if not k.startswith('@') or k == '@points'}
    elif isinstance(d, list):
        return [remove_at_keys(v) for v in d]
    else:
        return d
    
def string2numpy(s):
    # split the string into rows
    rows = s.split(' ')
    
    # split each row into elements and convert to float
    arr = np.array([list(map(float, filter(lambda x: x != '', row.split(',')))) for row in rows if row != ''])
    
    return arr

def reverse_matricies(matrix_list):
    for count, matrix in enumerate(matrix_list):
        matrix_list[count] = np.flip(matrix, axis=0)
        
    return matrix_list

def order_matricies(ordered_matrix_list, matrix_list):
    
    diff = 1
    
    while diff != 0:
        size_ordered_matrix_list_start = len(ordered_matrix_list)
        for count, matrix in enumerate(matrix_list):
            
            last_point = ordered_matrix_list[-1][-1, :]
            first_point = matrix[0, :]
            if type(first_point) != type(None):
                if ((first_point[0] == last_point[0])
                    and (first_point[1] == last_point[1])):
                    ordered_matrix_list.append(matrix)
                    del matrix_list[count]
                    
        size_ordered_matrix_list_finish = len(ordered_matrix_list)
        diff = size_ordered_matrix_list_start - size_ordered_matrix_list_finish
    
    return ordered_matrix_list

def write_polyline_svg(svg_dict, file, points, stroke="black", stroke_width=2, fill="white"):
    """
    Write a polyline to an SVG file.
    
    Arguments:
    - file: A file object for writing the SVG content.
    - points: An Nx2 NumPy array representing the points of the polyline.
    - stroke: A string representing the stroke color (default: "black").
    - stroke_width: An integer representing the stroke width (default: 2).
    - fill: A string representing the fill color (default: "none").
    """
    
    first_point = points[0, :]
    last_point = points[-1, :]
    if ((first_point[0] == last_point[0]) and (first_point[1] == last_point[1])):
        close_string = f'z" stroke="{stroke}" stroke-width="{stroke_width}" fill="{fill}" />\n'
    else:
        close_string = f'" stroke="{stroke}" stroke-width="{stroke_width}" fill="{fill}" />\n'
    
    view_box = get_view_box(svg_dict)
    width_height = get_width_height(svg_dict)
    # write the SVG content
    file.write('<svg width="{}" height="{}" viewBox="{} {} {} {}" xmlns="http://www.w3.org/2000/svg">\n'.format(*width_height, *view_box))
    file.write('<path d="M')
    for point in points:
        file.write(f'{point[0]},{point[1]} ')
    file.write(close_string)
    file.write('</svg>\n')
    
def get_format(format_string='exterior_cut'):
    formats = {
        'on line': {'fill': 'none', 'stroke': 'grey'},
        'guide': {'fill': 'none', 'stroke': 'blue'},
        'exterior': {'fill': 'black', 'stroke': 'black'},
        'interior': {'fill': 'white', 'stroke': 'black'},
        'pocket': {'fill': 'grey', 'stroke': 'none'},
        }
    
    return formats[format_string]

def onshape_svg_to_shaper_svg(input_path, output_path='output.svg', format_string='interior'):
    # Step 1: Read the SVG file
    with open(input_path, 'r') as f:
        svg_string = f.read()
    
    format_dict = get_format(format_string)
    fill = format_dict['fill']
    stroke = format_dict['stroke']
    
    # Step 2: Parse the SVG file using xmltodict
    svg_dict = xmltodict.parse(svg_string)
    
    clean_dict = remove_at_keys(svg_dict)
    
    elements = clean_dict['svg']['g']['g']
    
    merged_dict = {}
    for dictionary in elements:
        merged_dict.update(dictionary)
    
    for element_type in merged_dict:
        if element_type == 'polyline':
            polyline_matricies = []
            for dictionary in merged_dict[element_type]:
                polyline_matricies.append(string2numpy(dictionary['@points']))
            
            merged_polylines = []
            
            while len(polyline_matricies) > 0:
                ordered_matrix_list = []
                ordered_matrix_list.append(polyline_matricies[0])
                del polyline_matricies[0]
                
                ordered_matrix = order_matricies(ordered_matrix_list, polyline_matricies)
                polyline_matricies = reverse_matricies(polyline_matricies)
                ordered_matrix = order_matricies(ordered_matrix_list, polyline_matricies)
                
                merged_polylines.append(np.concatenate(ordered_matrix, axis=0))
        
    with open(output_path, 'w') as f:
        for count, polyline in enumerate(merged_polylines):
            points = polyline
            write_polyline_svg(svg_dict, f, points,
                               stroke=stroke, fill=fill)
            
onshape_svg_to_shaper_svg(input_path='Wall Brace.svg', output_path='Wall Brace Closed.svg')
