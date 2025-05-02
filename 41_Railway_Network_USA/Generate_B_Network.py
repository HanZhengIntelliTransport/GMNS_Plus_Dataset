import pandas as pd
import numpy as np
import shapely.geometry as geometry
from shapely import wkt, Point, LineString
import copy, ast


# 1. Read the origin network
all_node = pd.read_csv("./node.csv", low_memory=False)
all_link = pd.read_csv("./link.csv", low_memory=False)
all_yard = pd.read_csv("./rail_yards_polygons.csv", low_memory=False)
# all_yard = pd.read_csv("./rail_yards_polygons.csv", low_memory=False)

all_gate = pd.DataFrame(columns=['gate_node_id', 'belong_yard', 'x_coord', 'y_coord', 
                                 'direction','yard_node_id', 'closest_in', 'closest_out'])
all_bridge = pd.DataFrame()
all_yard_node = pd.DataFrame()
all_yard_link = pd.DataFrame()

# for key, yard in all_yard.iloc[:10].iterrows():
for key, yard in all_yard.iterrows():
    try:
        yard_id = yard['ID']
        print(yard_id)
        polygon = wkt.loads(yard['Polygon_WKT'])

        max_x, min_x = max([point[0] for point in polygon.exterior.coords]), min([point[0] for point in polygon.exterior.coords])
        max_y, min_y = max([point[1] for point in polygon.exterior.coords]), min([point[1] for point in polygon.exterior.coords])

        # 2. NODE
        # identify nodes in the rectangle yard zone (roughly)
        yard_node_temp = all_node[all_node['x_coord'] <= max_x]
        yard_node_temp = yard_node_temp[all_node['x_coord'] >= min_x]
        yard_node_temp = yard_node_temp[all_node['y_coord'] <= max_y]
        yard_node_temp = yard_node_temp[all_node['y_coord'] >= min_y]

        # identify nodes in the yard zone (accurately)
        yard_node = pd.DataFrame()
        for key_p, node in yard_node_temp.iterrows():
            point = Point(node['x_coord'], node['y_coord'])
            is_within = polygon.contains(point)
            if (is_within == True):
                yard_node = pd.concat([yard_node, node.to_frame().T], ignore_index=True)
        yard_node_id_list = yard_node['node_id'].to_list()
        
        # delete nodes from the origin network and generate nodes for A network
        all_node = all_node.merge(yard_node, how='left', indicator=True)
        all_node = all_node[all_node['_merge'] == 'left_only'].drop('_merge', axis=1)

        # create nodes for B network in the yards
        yard_node['yard_id'] = yard_id
        all_yard_node = pd.concat([all_yard_node, yard_node], ignore_index=True)

        # 3. LINK
        # identify links within the yards totally
        yard_link = all_link[all_link['from_node_id'].isin(yard_node_id_list)]
        yard_link = yard_link[all_link['to_node_id'].isin(yard_node_id_list)]

        # delete links from the origin network and generate links for A network
        all_link = all_link.merge(yard_link, how='left', indicator=True)
        all_link = all_link[all_link['_merge'] == 'left_only'].drop('_merge', axis=1)

        # create links for B network in the yards
        yard_link['yard_id'] = yard_id
        all_yard_link = pd.concat([all_yard_link, yard_link], ignore_index=True)

        # 4. BRIDGE
        # identify incoming bridge links and incoming bridge links from the origin network
        in_bridge_link = all_link[all_link['to_node_id'].isin(yard_node_id_list)]
        all_link = all_link.merge(in_bridge_link, how='left', indicator=True)
        all_link = all_link[all_link['_merge'] == 'left_only'].drop('_merge', axis=1)

        # extract incoming bridge links
        in_bridge_link['yard_id'] = yard_id
        in_bridge_link['direction'] = 'in'
        all_bridge = pd.concat([all_bridge, in_bridge_link], ignore_index=True)

        # extract gate nodes with respect to incoming bridge links
        for key, link in in_bridge_link.iterrows():
            gate_node_id = link['from_node_id']
            gate_node = all_node[all_node['node_id'] == gate_node_id].squeeze()
            x_coord = gate_node['x_coord']
            y_coord = gate_node['y_coord']
            all_gate.loc[len(all_gate)] = [gate_node['node_id'], yard_id, x_coord, y_coord, 'in', '', '', '']

        # identify outgoing bridge links and incoming bridge links from the origin network
        out_bridge_link = all_link[all_link['from_node_id'].isin(yard_node_id_list)]
        all_link = all_link.merge(out_bridge_link, how='left', indicator=True)
        all_link = all_link[all_link['_merge'] == 'left_only'].drop('_merge', axis=1)

        # extract outgoing bridge links
        out_bridge_link['yard_id'] = yard_id
        out_bridge_link['direction'] = 'out'
        all_bridge = pd.concat([all_bridge, out_bridge_link], ignore_index=True)

        # extract gate nodes with respect to outgoing bridge links
        for key, link in out_bridge_link.iterrows():
            gate_node_id = link['to_node_id']
            gate_node = all_node[all_node['node_id'] == gate_node_id].squeeze()
            x_coord = gate_node['x_coord']
            y_coord = gate_node['y_coord']
            all_gate.loc[len(all_gate)] = [gate_node['node_id'], yard_id, x_coord, y_coord, 'out', '', '', '']
        
        # identify gate nodes on the main direction
        coordinates = ast.literal_eval(yard['Main_Direction'])
        start_point, end_point = coordinates[0], coordinates[1] 
        main_direction = LineString([start_point, end_point])
        min_distance_start, min_distance_end = float('inf'), float('inf')
        closest_point_start, closest_point_end = None, None
        for key, gate in all_gate.iterrows():
            point_gate = Point(gate['x_coord'], gate['y_coord'])

            dist_start = point_gate.distance(Point(start_point))
            dist_end = point_gate.distance(Point(end_point))
            
            if dist_start < min_distance_start:
                min_distance_start = dist_start
                closest_point_start = key
            if dist_end < min_distance_end:
                min_distance_end = dist_end
                closest_point_end = key

        all_gate.at[closest_point_start, 'closest_in'] = 1
        all_gate.at[closest_point_end, 'closest_out'] = 1

    except Exception as e:
        print("ERROR with yard " + str(yard_id))
        continue

# 5. Merge network This is just a self-certification code that merges B network with B yard. It needs to be changed to merge with A network in the future.
all_node['resolution_type'] = 'Macro'
all_yard_node['resolution_type'] = 'Micro'
all_gate['resolution_type'] = 'Gate'
cross_resolution_node = pd.concat([all_node, all_yard_node, all_gate], axis = 0) 
cross_resolution_link = pd.concat([all_link, all_yard_link], axis = 0) 
cross_resolution_node.to_csv('C_Network_node_testing.csv', index = False)
cross_resolution_link.to_csv('C_Network_link_testing.csv', index = False)

# 6. output individual files
all_node.to_csv('B_Network_node.csv', index=False) # B network node
all_link.to_csv('B_Network_link.csv', index=False) # B network link
all_gate.to_csv('gate.csv', index=False) # gate node
all_bridge.to_csv('bridge.csv', index=False) # bridge link
all_yard_node.to_csv('B_Network_yard_node.csv', index=False) # B network yard node
all_yard_link.to_csv('B_Network_yard_link.csv', index=False) # B network yard link

print('finished!')
