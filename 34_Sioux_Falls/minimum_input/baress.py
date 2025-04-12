from pyomo.environ import *

def braess_paradox_demo():
    # Function to create and solve the model
    def create_model(include_extra_link=True):
        model = ConcreteModel(name="Traffic Assignment Problem User Equilibrium")
        
        # Sets
        model.nodes = RangeSet(1, 4)  # Nodes 1 to 4
        if include_extra_link:
            model.links = [(1, 2), (1, 3), (2, 4), (3, 4), (2, 3)]  # Including (2,3)
        else:
            model.links = [(1, 2), (1, 3), (2, 4), (3, 4)]  # Without (2,3)
        
        # Parameters
        # Link travel time parameter c_a (constant)
        # Initialize only for existing links
        c_a_init = {
            (1, 2): 0,
            (1, 3): 0,
            (2, 4): 0,
            (3, 4): 0
        }
        if include_extra_link:
            c_a_init[(2, 3)] = 0  # Assign appropriate value if needed
        
        model.c_a = Param(model.links, initialize=c_a_init, default=0)
        
        # Link cost parameter c_b (variable component)
        # Example: Travel time = c_a + 0.5 * c_b * flow
        c_b_init = {
            (1, 2): 10,  # Example value
            (1, 3): 10,
            (2, 4): 10,
            (3, 4): 10
        }
        if include_extra_link:
            c_b_init[(2, 3)] = 10  # Assign appropriate value if needed
        
        model.c_b = Param(model.links, initialize=c_b_init, default=10)
        
        # Demand and node indicators
        model.demand_vehicle = Param(initialize=4)  # Adjust demand as needed
        model.origin_node = Param(model.nodes, initialize={1: 1, 2: 0, 3: 0, 4: 0})
        model.destination_node = Param(model.nodes, initialize={1: 0, 2: 0, 3: 0, 4: 1})
        
        # Intermediate node indicator
        def intermediate_node_init(model, i):
            return (1 - model.origin_node[i]) * (1 - model.destination_node[i])
        
        model.intermediate_node = Param(model.nodes, initialize=intermediate_node_init)
        
        # Variables
        model.x = Var(model.links, domain=NonNegativeReals)  # Flow variable between nodes
        model.z = Var(domain=Reals)  # Objective function value
        
        # Objective function
        def ue_obj_rule(model):
            return model.z == sum(model.x[i, j] * (model.c_a[i, j] + 0.5 * model.c_b[i, j] * model.x[i, j]) for i, j in model.links)
        
        model.ue_obj = Constraint(rule=ue_obj_rule)
        
        # Flow constraints
        def flow_on_node_origin_rule(model, i):
            if model.origin_node[i] == 1:
                return sum(model.x[i, j] for j in model.nodes if (i, j) in model.links) == model.demand_vehicle
            return Constraint.Skip
        
        model.flow_on_node_origin = Constraint(model.nodes, rule=flow_on_node_origin_rule)
        
        def flow_on_node_destination_rule(model, i):
            if model.destination_node[i] == 1:
                return sum(model.x[j, i] for j in model.nodes if (j, i) in model.links) == model.demand_vehicle
            return Constraint.Skip
        
        model.flow_on_node_destination = Constraint(model.nodes, rule=flow_on_node_destination_rule)
        
        def flow_on_node_intermediate_rule(model, i):
            if model.intermediate_node[i] == 1:
                return (sum(model.x[i, j] for j in model.nodes if (i, j) in model.links) - 
                        sum(model.x[j, i] for j in model.nodes if (j, i) in model.links)) == 0
            return Constraint.Skip
        
        model.flow_on_node_intermediate = Constraint(model.nodes, rule=flow_on_node_intermediate_rule)
        
        # Objective
        model.obj = Objective(expr=model.z, sense=minimize)
        
        return model
    
    # Solve the model
    def solve_model(model, solver_name='gurobi'):
        solver = SolverFactory(solver_name)
        result = solver.solve(model, tee=False)
        if (result.solver.status != SolverStatus.ok) or (result.solver.termination_condition != TerminationCondition.optimal):
            raise ValueError("Solver did not find an optimal solution")
        return result
    
    # Create and solve Network A (Without Extra Link)
    print("=== Network A: Without Extra Link (2,3) ===")
    model_A = create_model(include_extra_link=False)
    try:
        solve_model(model_A)
    except ValueError as e:
        print(e)
        return
    
    # Display results for Network A
    print("\nFlow Distribution (Network A):")
    for i, j in model_A.links:
        print(f"Flow on link ({i}, {j}): {model_A.x[i, j].value}")
    total_cost_A = sum(model_A.x[i, j].value * (model_A.c_a[i, j] + 0.5 * model_A.c_b[i, j] * model_A.x[i, j].value) for i, j in model_A.links)
    print(f"Total Cost (Network A): {total_cost_A}\n")
    
    # Create and solve Network B (With Extra Link)
    print("=== Network B: With Extra Link (2,3) ===")
    model_B = create_model(include_extra_link=True)
    try:
        solve_model(model_B)
    except ValueError as e:
        print(e)
        return
    
    # Display results for Network B
    print("\nFlow Distribution (Network B):")
    for i, j in model_B.links:
        print(f"Flow on link ({i}, {j}): {model_B.x[i, j].value}")
    total_cost_B = sum(model_B.x[i, j].value * (model_B.c_a[i, j] + 0.5 * model_B.c_b[i, j] * model_B.x[i, j].value) for i, j in model_B.links)
    print(f"Total Cost (Network B): {total_cost_B}\n")
    
    # Compare Total Costs
    print("=== Comparison ===")
    print(f"Total Cost without extra link: {total_cost_A}")
    print(f"Total Cost with extra link: {total_cost_B}")
    if total_cost_B > total_cost_A:
        print("Braess's Paradox Occurs: Adding the extra link increased the total cost.")
    elif total_cost_B < total_cost_A:
        print("Unexpected Result: Adding the extra link decreased the total cost.")
    else:
        print("No Change in Total Cost: Adding the extra link did not affect the total cost.")

# Run the demonstration
braess_paradox_demo()
