import pandas as pd
import DTALite as dta


def check_and_sort_files(node_file='node.csv', link_file='link.csv'):
    """
    Check if node_file is sorted by node_id and link_file is sorted first by
    from_node_id and then by to_node_id. If not, sort the files and save them.

    Parameters:
    - node_file: str, path to the node CSV file.
    - link_file: str, path to the link CSV file.
    """

    # Check if node.csv is sorted by node_id
    node_df = pd.read_csv(node_file)
    if not node_df['node_id'].is_monotonic_increasing:
        print(f"{node_file} is not sorted by node_id. Sorting now.")
        node_df.sort_values('node_id', inplace=True)
        node_df.to_csv(node_file, index=False)
    else:
        print(f"{node_file} is already sorted by node_id.")

    # Check if link.csv is sorted by from_node_id and to_node_id (first sort by from_node_id, then to_node_id)
    link_df = pd.read_csv(link_file)
    sorted_link_df = link_df.sort_values(by=['from_node_id', 'to_node_id']).reset_index(drop=True)
    current_link_order = link_df[['from_node_id', 'to_node_id']].reset_index(drop=True)

    if not current_link_order.equals(sorted_link_df[['from_node_id', 'to_node_id']]):
        print(f"{link_file} is not sorted by from_node_id and to_node_id. Sorting now.")
        sorted_link_df.to_csv(link_file, index=False)
    else:
        print(f"{link_file} is already sorted by from_node_id and to_node_id.")


# Use the function to check and sort the files, then run the assignment.
check_and_sort_files()
dta.assignment()

# dta.simulation()