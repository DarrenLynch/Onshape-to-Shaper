import xmltodict
import copy

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
        
    def _add_shaper_xmlns(self):
        self.svg_dict['svg']['@xmlns:shaper']\
            ="http://www.shapertools.com/namespaces/shaper"
        
    def polyline_to_path(self):
        '''
        Take all polylines in the dictionary, convert them to paths
        
        Returns
        -------
        None.

        '''
        empty_group_dict = OrderedDict([('@d', None)])
        cleaned_dicts = remove_at_keys(self.original_svg_dict)
        
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
                    
        for index in sorted(self.removed_polyline_index, reverse=True):
            del self.svg_dict['svg']['g']['g'][index]
            
            
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
                    polyline_type = type(self.original_svg_dict['svg']['g']['g'][idx[0]]['polyline'])
                    
                    if i > 0 and polyline_type == list:
                        self.original_svg_dict['svg']['g']['g'][idx[0]]['polyline'].extend(
                            self.original_svg_dict['svg']['g']['g'][idx[i]]['polyline'])
                        
                    elif i > 0 and polyline_type == OrderedDict:
                        raise ValueError("polyline is type OrderedDict, expected list")
                        
        
        index_to_remove = []
        for idx in idxs:
            if (len(idx) > 1):
                for i, appending_lines in enumerate(idx):
                    if i > 0:
                        index_to_remove.append(idx[i])
                        
        index_to_remove.sort(reverse=True)
        
        for index in index_to_remove:
            del self.original_svg_dict['svg']['g']['g'][index]
            del self.svg_dict['svg']['g']['g'][index]
                        
        
        return groups, idxs
            
    def tosvg(self, output_path):
        '''
        export the xml back to svg

        Parameters
        ----------
        output_path : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        xml_str = xmltodict.unparse(self.svg_dict)
        
        # Write the XML string to a file with .svg extension
        with open(output_path, 'w') as f:
            f.write(xml_str)
            
    def decode_format(self):
        '''
        re-format translating from OnShape to colours to shaper depth and cut

        Returns
        -------
        None.

        '''
        #line width is type
            #1 - inside
            #2 - outside
            #3 - pocket
            #4 - on-line
            #5 - Guide
        
        #line colour is depth
            #color in hex is in 1/10th mm
            
        #IMPORTANT! Depth should be first because color is used and will be 
        #changed after because shaper uses color to define cut type
        
        #Define the Shaper Formats
        formats = {
            'interior': {'fill': 'white', 'stroke': 'black'},
            'exterior': {'fill': 'black', 'stroke': 'black'},
            'pocket': {'fill': 'grey', 'stroke': 'none'},
            'on line': {'fill': 'none', 'stroke': 'grey'},
            'guide': {'fill': 'none', 'stroke': 'blue'},
            }
        
        
        for count, _dict in enumerate(self.svg_dict['svg']['g']['g']):
            if '@stroke' in _dict:
                colour = _dict['@stroke']
                colour = colour.strip('#')
                
                depth = float(colour)/10
                
                self.svg_dict['svg']['g']['g'][count]['@shaper:cutDepth'] \
                    = str(depth) + 'mm'
                    
            if '@stroke-width' in _dict:
                _type = int(float(_dict['@stroke-width'])/12)
                if (_type < 1) or (_type > 5):
                    _type = 4
                
                key = list(formats.keys())[_type-1]
                
                self.svg_dict['svg']['g']['g'][count]['@stroke'] \
                    = formats[key]['stroke']
                self.svg_dict['svg']['g']['g'][count]['@fill'] \
                    = formats[key]['fill']
    
    def _remove_boarder(self):
        '''
        remove the rectangle OnShape outputs automatically but is not part of sketch

        Returns
        -------
        None.

        '''
        for count, _dict in enumerate(self.svg_dict['svg']['g']['g']):
            if 'rect' in _dict:
                del self.svg_dict['svg']['g']['g'][count]
                break
            
    def _list_single_polylines(self):
        for count, _dict in enumerate(self.svg_dict['svg']['g']['g']):
            if 'polyline' in _dict:
                if type(_dict['polyline']) is OrderedDict:
                    self.original_svg_dict['svg']['g']['g'][count]['polyline'] = \
                        [self.original_svg_dict['svg']['g']['g'][count]['polyline']]
    
    def plot_paths_rand_color(self):
        '''
        plot lines with random colors to make sure the joins happen where expected

        Returns
        -------
        None.

        '''
        import matplotlib.pyplot as plt
        from  matplotlib.lines import Line2D
        
        paths = []
        for _dict in self.svg_dict['svg']['g']['g']:
            if 'path' in _dict:
                paths.append(_dict)
        
        # Create a figure and axis
        fig, ax = plt.subplots()
        
        max_x = None
        min_x = None
        
        max_y = None
        min_y = None
        
        # Plot each path
        for path_data in paths:
            path_str = path_data['path']["@d"]
            
            path_str = path_str.strip('M')
            path_str = path_str.strip('z')
            
            col = (np.random.random(), np.random.random(), np.random.random())
            
            path = string2numpy(path_str)
            path_patch = Line2D(path[:, 0], path[:, 1], color=col)
            
            ax.add_line(path_patch)
            
            if max_x == None:
                max_x = np.max(path[:, 0])
            if min_x == None:
                min_x = np.min(path[:, 0])
            if max_y == None:
                max_y = np.max(path[:, 1])
            if min_y == None:
                min_y = np.min(path[:, 1])
            
            if np.max(path[:, 0]) > max_x:
                max_x = np.max(path[:, 0])
            if np.min(path[:, 0]) < min_x:
                min_x = np.min(path[:, 0])
            if np.max(path[:, 1]) > max_y:
                max_y = np.max(path[:, 1])
            if np.min(path[:, 1]) < min_y:
                min_y = np.min(path[:, 1])
        
        ax.set_xlim(max_x, min_x)
        ax.set_ylim(max_y, min_y)
        
        # Show the plot
        plt.show()
        
    def onshape2shaper(self, output_path, plot_line_checker=False):
        '''
        A one liner to call methods in order

        Parameters
        ----------
        output_path : TYPE
            DESCRIPTION.
        plot_line_checker : TYPE, optional
            DESCRIPTION. The default is False.

        Returns
        -------
        None.

        '''
        self.read_svg()
        self._add_shaper_xmlns()
        self._list_single_polylines()
        self.sort_colours()

        self.polyline_to_path()
        self._remove_boarder()
        self.decode_format()
        
        self.tosvg(output_path)
        
        if plot_line_checker:
            self.plot_paths_rand_color()
        
        
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
            
            polyline1 = ordered_matrix_list[-1]
            polyline2 = matrix
            
            #ensure you do not add a line that is identical and traces back on 
            #itself
            if check_identical_polyline(polyline1, polyline2):
                del matrix_list[count]
                continue
            
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
    
    points_string = 'M' + points_string
    
    first_point = points[0, :]
    last_point = points[-1, :]
    if ((first_point[0] == last_point[0]) and (first_point[1] == last_point[1])):
        points_string = points_string + 'z'
        
    return points_string

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

def check_identical_polyline(polyline1, polyline2):
    '''
    Check if two poly lines are perfectly identical, this only evaluates points

    Parameters
    ----------
    polyline1 : TYPE
        DESCRIPTION.
    polyline2 : TYPE
        DESCRIPTION.

    Returns
    -------
    bool
        DESCRIPTION.

    '''
    # Check if the number of points is the same
    if len(polyline1) != len(polyline2):
        return False
    
    # Check if all corresponding points match
    if not np.allclose(polyline1, polyline2):
        return False
    
    return True
    
if __name__ == "__main__":
    import pathlib
    
    input_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                              'Finger test/Cut 1 - Hole.svg')
    output_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                               'Finger test/Cut 1 - Hole - closed.svg')
    
    svg = vector_object(input_path)
    svg.onshape2shaper(output_path, plot_line_checker=True)
    