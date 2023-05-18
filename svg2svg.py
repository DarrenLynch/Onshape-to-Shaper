import pathlib
import xmltodict
import copy
import traceback

from collections import OrderedDict

import numpy as np

class vector_object():
    
    def __init__(self, input_path):
        
        self.input_path = input_path
        self.svg_dict = {}
        self.original_svg_dict = {}
        self.vector_grouped_dict = {}
        self.polylines = []
        self.removed_polyline_index = []
        
    def read_svg(self):
        '''
        Read an SVG from the input path, convert it to dictionary

        Returns
        -------
        None.

        '''
        # Step 1: Read the SVG file
        with open(self.input_path, 'r') as f:
            svg_string = f.read()
        
        # Step 2: Parse the SVG file using xmltodict
        self.svg_dict = xmltodict.parse(svg_string)
        self.original_svg_dict = copy.deepcopy(self.svg_dict)
        
    def polyline_to_path(self):
        '''
        Take all polylines in the dictionary, convert them to paths
        
        Returns
        -------
        None.

        '''
        empty_group_dict = OrderedDict([('@d', None)])
        cleaned_dicts = remove_at_keys(self.original_svg_dict)
        
        polylines_to_remove = []
        for _dict in enumerate(zip(cleaned_dicts['svg']['g']['g'], 
                         self.original_svg_dict['svg']['g']['g'])):
            if _dict[1][0]:
                entity_type = list(_dict[1][0].keys())[0]
                
                if entity_type == 'polyline':
                    
                    polyline_list = _dict[1][1]['polyline']
                    polyline_list_cleaned = _dict[1][0]['polyline']
                    polyline_matricies = []
                    
                    for (points_dict, 
                         points_dict_cleaned) in zip(polyline_list, 
                                                     polyline_list_cleaned):
                        if points_dict_cleaned:
                            polyline_matricies.append(string2numpy(points_dict['@points']))
                            
                    #Merged polyline is the ordered list to make into a path
                    merged_polylines = match_polylines_forward_backwards(polyline_matricies)
                    #match_polylines_2(polyline_matricies)
                    for path in merged_polylines:
                        
                        path_string = numpy2pathstring(path)
                        
                        new_dict = copy.deepcopy(_dict[1][1])
                        del new_dict["polyline"]
                        new_dict['path'] = copy.deepcopy(empty_group_dict)
                        
                        new_dict['path']['@d'] = path_string
                        
                        self.svg_dict['svg']['g']['g'].append(new_dict)
                    
                    self.removed_polyline_index.append(_dict[0])
        print(len(self.svg_dict['svg']['g']['g']))
        for index in sorted(self.removed_polyline_index, reverse=True):
            del self.svg_dict['svg']['g']['g'][index]
        print(len(self.svg_dict['svg']['g']['g']))
            
    def sort_colours(self):
        '''
        Identify all polylines with the same properties, and merge them

        Returns
        -------
        groups : TYPE
            DESCRIPTION.
        idxs : TYPE
            DESCRIPTION.

        '''
        groups, idxs = get_grouped_dicts(self.original_svg_dict['svg']['g']['g'], 'polyline')
        
        for group, idx in zip(groups, idxs):
            if (len(group) > 1) and ('polyline' in group[0].keys()):
                for i, appending_lines in enumerate(group):
                    if i > 0:
                        self.original_svg_dict['svg']['g']['g'][idx[0]]['polyline'].extend(
                            self.original_svg_dict['svg']['g']['g'][idx[i]]['polyline'])
        
        for group, idx in zip(groups, idxs):
            if (len(group) > 1) and ('polyline' in group[0].keys()):
                for i, appending_lines in enumerate(group):
                    if i > 0:
                        del self.original_svg_dict['svg']['g']['g'][idx[i]]
        
        return groups, idxs
            
    def tosvg(self, output_path):
        xml_str = xmltodict.unparse(self.svg_dict)
        
        # Write the XML string to a file with .svg extension
        with open(output_path, 'w') as f:
            f.write(xml_str)

def remove_at_keys(d):
    '''
    Clean a dictionary of keys prepended with @

    Parameters
    ----------
    d : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    '''
    if isinstance(d, dict):
        return {k: remove_at_keys(v) for k, v in d.items() \
                if not k.startswith('@') or k == '@points'}
    elif isinstance(d, list):
        return [remove_at_keys(v) for v in d]
    else:
        return d
    
def string2numpy(s):
    '''
    Take a string of comma seperated, space row delimited table and return numpy array

    Parameters
    ----------
    s : TYPE
        DESCRIPTION.

    Returns
    -------
    arr : TYPE
        DESCRIPTION.

    '''
    # split the string into rows
    rows = s.split(' ')
    
    # split each row into elements and convert to float
    arr = np.array([list(map(float, filter(lambda x: x != '', 
                                           row.split(','))\
                             )) for row in rows if row != ''])
    
    return arr

def order_matricies(ordered_matrix_list, matrix_list):
    '''
    Order a list of matrixies so that the polylines joint in order

    Parameters
    ----------
    ordered_matrix_list : TYPE
        DESCRIPTION.
    matrix_list : TYPE
        DESCRIPTION.

    Returns
    -------
    ordered_matrix_list : TYPE
        DESCRIPTION.

    '''
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

def reverse_matricies(matrix_list):
    '''
    take a list of matricies, and reverse them all, but dont rearange them

    Parameters
    ----------
    matrix_list : TYPE
        DESCRIPTION.

    Returns
    -------
    reversed_list : TYPE
        DESCRIPTION.

    '''
    reversed_list = []
    for count, matrix in enumerate(matrix_list):
        reversed_list.append(np.flip(matrix, axis=0))
        
    return reversed_list

def match_polylines_forward_backwards(polylines):
    '''
    Try and match matricies end to end, but also incase they are dran backwards

    Parameters
    ----------
    polylines : TYPE
        DESCRIPTION.

    Returns
    -------
    merged_polylines : TYPE
        DESCRIPTION.

    '''
    polyline_matricies = copy.deepcopy(polylines)
    merged_polylines = []
    
    while len(polyline_matricies) > 0:
        ordered_matrix_list = []
        ordered_matrix_list.append(polyline_matricies[0])
        del polyline_matricies[0]
        
        ordered_matrix = order_matricies(ordered_matrix_list, polyline_matricies)
        
        diff = 1
        
        while diff > 0:
            start_length = len(ordered_matrix)
            polyline_matricies = reverse_matricies(polyline_matricies)
            ordered_matrix = order_matricies(ordered_matrix_list, polyline_matricies)
            
            end_length = len(ordered_matrix)
            diff = end_length - start_length
            
        merged_polylines.append(np.concatenate(ordered_matrix, axis=0))
    
    
    return merged_polylines

def numpy2pathstring(points):
    '''
    Take a numpy array, convert them back to comma space seperated strings, prepending M

    Parameters
    ----------
    points : TYPE
        DESCRIPTION.

    Returns
    -------
    TYPE
        DESCRIPTION.

    '''
    # Convert to string with comma separated x and y values and space 
    #separated between each coordinate
    points_string = ' '.join([f"{x:.2f},{y:.2f}" for x, y in points])
    return 'M' + points_string

def compare_dicts(dict1, dict2, key_to_ignore):
    '''
    Take two dicts, compare if their properties are identical except for one key

    Parameters
    ----------
    dict1 : TYPE
        DESCRIPTION.
    dict2 : TYPE
        DESCRIPTION.
    key_to_ignore : TYPE
        DESCRIPTION.

    Returns
    -------
    bool
        DESCRIPTION.

    '''
    # Check if the dictionaries have the same keys (except for the ignored key)
    dict1_keys = set(dict1.keys()) - {key_to_ignore}
    dict2_keys = set(dict2.keys()) - {key_to_ignore}
    if dict1_keys != dict2_keys:
        return False

    # Check if the values of all keys (except for the ignored key) are the same
    for key in dict1_keys:
        if dict1[key] != dict2[key]:
            return False

    # Check if the ignored key is present in both dictionaries
    if key_to_ignore not in dict1 or key_to_ignore not in dict2:
        return False

    # Check if the values of the ignored key are different
    if dict1[key_to_ignore] == dict2[key_to_ignore]:
        return False

    # If we've gotten this far, the dictionaries are identical except for the 
    #ignored key
    return True

def get_grouped_dicts(dict_list, key_to_ignore):
    '''
    Takes a list of dicts, returns a list of groups

    Parameters
    ----------
    dict_list : TYPE
        DESCRIPTION.
    key_to_ignore : TYPE
        DESCRIPTION.

    Returns
    -------
    groups : TYPE
        DESCRIPTION.
    indices : TYPE
        DESCRIPTION.

    '''
    # Initialize an empty list to store the groups of similar dictionaries
    groups = []
    indices = []
    
    for i, d in enumerate(dict_list):
        found = False
        for g in groups:
            if all(d[k] == g[0][k] for k in d if k != key_to_ignore):
                g.append(d)
                found = True
                break
        if not found:
            groups.append([d])
            indices.append([i])
        else:
            indices[groups.index(g)].append(i)
            
    return groups, indices
    
if __name__ == "__main__":
    svg = vector_object('Test2.svg')
    svg.read_svg()
    groups, index = svg.sort_colours()
    svg.polyline_to_path()
    svg.tosvg('Test2output.svg')