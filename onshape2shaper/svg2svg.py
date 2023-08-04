import xmltodict
import copy
import re

import networkx as nx
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
        
        self.pixels_per_mm = 5
        self.is_shaper_added = False
        
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
        self.is_shaper_added = True
    def _get_pixels_per_mm(self):
        global height_in_units
        height_in_units = self.svg_dict['svg']['@height']
        
        def split_string(string):
            pattern = r'(\d+(\.\d+)?)\s*(\D+)'
            match = re.match(pattern, string)
            
            if match:
                number = float(match.group(1))
                unit = match.group(3)
                result = [number, unit]
                return result
            else:
                return None
            
        match = split_string(height_in_units)
        
        if match[1] != 'mm':
            raise Exception('This conversion currently only support mm as a unit')
            
        else:
            height_in_mm = match[0]
            height_in_pixels = float(string2numpy(
                self.svg_dict['svg']['@viewBox'])[3])
            
            self.pixels_per_mm = height_in_pixels/height_in_mm
        
    def polyline_to_path(self):
        '''
        Take all polylines in the dictionary, convert them to paths
        
        Returns
        -------
        None.

        '''
        cleaned_dicts = remove_at_keys(copy.deepcopy(self.svg_dict))
        for _dict in enumerate(zip(cleaned_dicts['svg']['g']['g'], 
                         self.svg_dict['svg']['g']['g'])):
            if _dict[1][0]:
                
                entity_type = list(_dict[1][0].keys())[0]
                stroke_colour = _dict[1][1]['@stroke']
                if (entity_type == 'polyline')\
                  and (stroke_colour.strip('#') == 'ff0000'):
                        
                    merged_polylines = self.to_merge_polylines(_dict)
                    
                    self.to_anchor(_dict, merged_polylines)
                
                elif entity_type == 'polyline':
                    
                    merged_polylines = self.to_merge_polylines(_dict)
                    self.to_paths(_dict, merged_polylines)
                    
        for index in sorted(self.removed_polyline_index, reverse=True):
            del self.svg_dict['svg']['g']['g'][index]
            
    def to_merge_polylines(self, _dict):
        polyline_list = _dict[1][1]['polyline']
        polyline_list_cleaned = _dict[1][0]['polyline']
        polyline_matricies = []
        if type(polyline_list) != list:
            polyline_list = [polyline_list]
            
        for (points_dict, 
             points_dict_cleaned) in zip(polyline_list, 
                                         polyline_list_cleaned):
                                         
            if points_dict_cleaned:
                polyline_matricies.append(string2numpy(points_dict['@points']))
                
        #Merged polyline is the ordered list to make into a path
        merged_polylines = order_polylines(polyline_matricies)
        
        return merged_polylines
        
    def to_paths(self, _dict, merged_polylines):
        empty_group_dict = OrderedDict([('@d', None)])
        
        for path in merged_polylines:
            
            path_string = numpy2pathstring(path)
            
            new_dict = copy.deepcopy(_dict[1][1])
            del new_dict["polyline"]
            new_dict['path'] = copy.deepcopy(empty_group_dict)
            
            new_dict['path']['@d'] = path_string
            
            self.svg_dict['svg']['g']['g'].append(new_dict)
        
        self.removed_polyline_index.append(_dict[0])
        
    def to_anchor(self, _dict, merged_polylines):
        
        self.svg_dict['svg']['g']['g'][_dict[0]]['polygon']=[]
        
        for polyline in merged_polylines:
            cleaned_polyline = clean_anchor(polyline)
            

            # Create a new 'polygon' dictionary with the desired attributes
            polygon_dict = {
                '@points': to_points_string(cleaned_polyline),
                '@fill': 'ff0000'
            }
            
            # Replace the 'polyline' dictionary with the 'polygon' dictionary
            self.svg_dict['svg']['g']['g'][_dict[0]]['polygon'].append(polygon_dict)
            
        del self.svg_dict['svg']['g']['g'][_dict[0]]['polyline']
            
    
    def sort_colours(self):
        global groups, idx
        '''
        Identify all polylines with the same properties, and merge them

        Returns
        -------
        groups : TYPE
            DESCRIPTION.
        idxs : TYPE
            DESCRIPTION.

        '''
        self.svg_dict['svg']['g']['g'] = filter_dict_keys(self.svg_dict['svg']['g']['g'], 'polyline')
        groups, idxs = get_grouped_dicts(self.svg_dict['svg']['g']['g'], 'polyline')
        
        self.svg_dict['svg']['g']['g'] = []
        
        for i, group in enumerate(groups):
            if (len(group) > 1) and ('polyline' in group[0].keys()):
                merged_group = copy.deepcopy(group[0])
                merged_group['polyline'] = merge_dicts_with_polyline(group)
                self.svg_dict['svg']['g']['g'].append(merged_group)
            elif (len(group) == 1) and ('polyline' in group[0].keys()):
                self.svg_dict['svg']['g']['g'].append(group[0])
        
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
        
        xml_str = xmltodict.unparse(self.svg_dict, pretty=True)
        
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
            #0.2mm - inside
            #0.4mm - outside
            #0.6mm - pocket
            #0.8mm - on-line
            #1.0mm - Guide
            #1.2mm - Anchor
        
        
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
            'anchor': {'fill': '#ff0000', 'stroke': '#ff0000'},
            }
        
        
        for count, _dict in enumerate(self.svg_dict['svg']['g']['g']):
            if '@stroke' in _dict:
                colour = _dict['@stroke']
                colour = colour.strip('#')
                
                try:
                    depth = float(colour)/10
                    
                    if 'path' in self.svg_dict['svg']['g']['g'][count]\
                        and self.is_shaper_added:
                        self.svg_dict['svg']['g']['g'][count]['path']['@shaper:cutDepth'] \
                            = str(depth) + 'mm'
                        
                except:
                    pass
                    
            if colour.strip('#') == 'ff0000':
                _type = 6
                
                key = list(formats.keys())[_type-1]
                
                del self.svg_dict['svg']['g']['g'][count]['@stroke'] #\
                    #= formats[key]['stroke']
                self.svg_dict['svg']['g']['g'][count]['@fill'] \
                    = formats[key]['fill']
                
            elif '@stroke-width' in _dict:
                _type = int(round((float(_dict['@stroke-width'])\
                                   /self.pixels_per_mm)*10)/2)
                
                if (_type < 1) or (_type > 6):
                    _type = 4
                
                key = list(formats.keys())[_type-1]
                
                self.svg_dict['svg']['g']['g'][count]['@stroke'] \
                    = formats[key]['stroke']
                self.svg_dict['svg']['g']['g'][count]['@fill'] \
                    = formats[key]['fill']
                
                '''
                #at some point return stroke width to normal
                self.svg_dict['svg']['g']['g'][count]['@stroke'] \
                    = formats[key]['stroke']
                '''
                
    def remove_default_stroke(self):
        del self.svg_dict['svg']['g']['@stroke']
    
    def flatten_groups(self):
        self.svg_dict = {**self.svg_dict, **self.svg_dict['svg']['g']['g']}
    
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
                    self.svg_dict['svg']['g']['g'][count]['polyline'] = \
                        [self.svg_dict['svg']['g']['g'][count]['polyline']]
    
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
        
        ax.set_xlim(max_x*1.1, min_x - np.abs(min_x*0.1))
        ax.set_ylim(max_y*1.1, min_y - np.abs(min_y*0.1))
        
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
        self._get_pixels_per_mm()
        self._add_shaper_xmlns()
        self._list_single_polylines()
        self.sort_colours()

        self.polyline_to_path()
        self._remove_boarder()
        self.decode_format()
        
        self.remove_default_stroke()
        
        self.tosvg(output_path)
        
        if plot_line_checker:
            self.plot_paths_rand_color()
        
        self.tosvg(output_path)
        
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

def order_polylines(polyline_list):
    """
    Orders the points within each polyline and merges connected polylines in a list of 2D polylines.
    
    Args:
        polyline_list (list): List of polylines, where each polyline is represented as a list of points.
            Each point is a 2D coordinate represented as a list or tuple.
    
    Returns:
        list: List of ordered and merged polylines, where each polyline is represented as a list of points.
    """
    # Step 1: Build the graph
    graph = nx.Graph()
    for polyline in polyline_list:
        # Add edges between consecutive points in the polyline
        for i in range(len(polyline) - 1):
            point1 = tuple(polyline[i])
            point2 = tuple(polyline[i + 1])
            graph.add_edge(point1, point2)

    # Step 2: Identify connected components
    connected_components = list(nx.connected_components(graph))

    # Step 3: Merge and order polylines within each connected component
    merged_polylines = []
    for component in connected_components:
        merged_polyline = []
        endpoint_nodes = []
        for point in component:
            degree = graph.degree[point]
            if degree == 1 or degree > 2:
                endpoint_nodes.append(point)
        if len(endpoint_nodes) >= 2:
            start_point, end_point = endpoint_nodes[0], endpoint_nodes[1]
            dfs_traversal(graph, start_point, end_point, merged_polyline)
        elif len(endpoint_nodes) == 0:
            start_point = list(component)[0]
            dfs_traversal(graph, 
                          start_point, 
                          start_point, 
                          merged_polyline, 
                          is_closed=True)
        else:
            raise ValueError("Endpoint detection failed for a polyline.")
        if merged_polyline:
            merged_polylines.append(np.array(merged_polyline))

    return merged_polylines

def dfs_traversal(graph, 
                  start_point, 
                  end_point, 
                  merged_polyline, 
                  is_closed=False):
    """
    Performs depth-first traversal on a graph starting from the start_point and ending at the end_point.
    Appends the visited points to the merged_polyline.
    
    Args:
        graph (networkx.Graph): Graph representing the connectivity between points.
        start_point: Starting point for the traversal.
        end_point: Ending point for the traversal.
        merged_polyline (list): List to store the merged polyline points.
    """
    stack = [start_point]
    visited = set()
    while stack:
        current_point = stack.pop()
        visited.add(current_point)
        merged_polyline.append(list(current_point))
        if current_point == end_point and len(visited) == len(graph.nodes):
            break
        neighbors = list(graph.neighbors(current_point))
        for neighbor in neighbors:
            if neighbor not in visited:
                stack.append(neighbor)
        
    if is_closed:
        merged_polyline.append(list(start_point))


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

def to_points_string(points):
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

def clean_anchor(polyline):
    # Find indices where consecutive duplicates occur
    duplicate_indices = np.flatnonzero(np.all(np.diff(polyline, axis=0) == 0, axis=1))

    # Remove consecutive duplicates
    filtered_polyline = np.delete(polyline, duplicate_indices + 1, axis=0)
    
    if np.array_equal(filtered_polyline[0], filtered_polyline[-1]):
        # Remove the last point
        filtered_polyline = filtered_polyline[:-1]
        
    size = filtered_polyline.shape[0]
    if size != 3:
        raise Exception('Anchor should have 3 points, has {}'.format(size))
    else:
        return filtered_polyline
    
def filter_dict_keys(dict_list, key_to_keep):
    """
    Filters a dictionary to retain only the keys that are "@stroke", "@fill", "@line-width",
    and a specified key_to_keep.
    
    Args:
        dictionary (dict): The input dictionary.
        key_to_keep (str): The key that should be retained in the filtered dictionary.
        
    Returns:
        dict: A new dictionary containing only the filtered keys.
    """
    for i, d in enumerate(dict_list):
        keys_to_filter = ["@stroke", "@fill", "@stroke-width"]
        keys_to_filter.append(key_to_keep)
        
        dict_list[i] = {key: value for key, value in d.items() if key in keys_to_filter}
    return dict_list

def merge_dicts_with_polyline(dicts_list):
    """
    Merges a list of dictionaries by joining the 'polyline' lists.

    Args:
        dicts_list (list): List of dictionaries, where each dictionary has a 'polyline' key with a list value.

    Returns:
        dict: A new dictionary with the 'polyline' list joined from all input dictionaries.
    """
    #merged_dict = {}
    merged_polyline = []
    
    for dictionary in dicts_list:
        if 'polyline' in dictionary and type(dictionary['polyline']) == list:
            merged_polyline.extend(dictionary['polyline'])
        elif 'polyline' in dictionary and type(dictionary['polyline']) == dict:
                merged_polyline.append(dictionary['polyline'])
            
    #merged_dict['polyline'] = merged_polyline
    return merged_polyline
    
if __name__ == "__main__":
    import pathlib
    
    #Test 1
    input_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                              'Finger test/A-frame.svg')
        
    output_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                               'Finger test/A-frame - closed.svg')
    
    svg = vector_object(input_path)
    svg.onshape2shaper(output_path, plot_line_checker=True)
    
    #Test 2
    input_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                              'Finger test/Test2.svg')
        
    output_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                               'Finger test/Test2 - closed.svg')
    
    svg = vector_object(input_path)
    svg.onshape2shaper(output_path, plot_line_checker=True)
    
    #Test 3
    input_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                              'Finger test/radius_cut.svg')
        
    output_path = pathlib.Path('/Users/darrenlynch/Documents/Shaper Origin/'+\
                               'Finger test/radius_cut - closed.svg')
    
    svg = vector_object(input_path)
    svg.onshape2shaper(output_path, plot_line_checker=True)
    
    