# -*- coding: utf-8 -*-
"""
Created on Sat Nov  2 19:41:58 2024

@author: xzhou
"""
from pyomo.environ import *

# Model
model = ConcreteModel(name="Traffic Assignment Problem User Equilibrium")

# Sets
model.nodes = RangeSet(1, 4)  # Nodes 1 to 4
model.links = [(1, 2), (1, 3), (2, 4), (3, 4), (3, 2)]  # Link pairs

# Parameters
# Link travel time parameter c_a
model.free_flow_time = Param(model.links, initialize={
    (1, 2): 60,
    (1, 3): 10,
    (2, 4): 10,
    (3, 4): 60,
    (3, 2): 10
})

# Link cost parameter c_b
model.capacity = Param(model.links, initialize={
    (1, 2): 1,
    (1, 3): 10,
    (2, 4): 10,
    (3, 4): 1,
    (3, 2): 1
})

# BPR parameters
alpha = 0.15
beta = 4

# Demand and node indicators
model.demand_vehicle = Param(initialize=6)
model.origin_node = Param(model.nodes, initialize={1: 1, 2: 0, 3: 0, 4: 0})
model.destination_node = Param(model.nodes, initialize={1: 0, 2: 0, 3: 0, 4: 1})

# Intermediate node indicator
def intermediate_node_init(model, i):
    return (1 - model.origin_node[i]) * (1 - model.destination_node[i])

model.intermediate_node = Param(model.nodes, initialize=intermediate_node_init)

# Variables
model.x = Var(model.links, domain=NonNegativeReals)  # Flow variable between nodes
model.z = Var(domain=Reals)  # Objective function value

# Define the objective function with the modified BPR form
def ue_obj_rule(model):
    return model.z == sum(
        model.free_flow_time[i, j] * (model.x[i, j] + (alpha * model.x[i, j] ** (beta + 1)) /
                                      (model.capacity[i, j] ** beta * (beta + 1)))
        for (i, j) in model.links
    )

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

# Solve
solver = SolverFactory('ipopt')  # or other solver like 'ipopt' if available
solver.solve(model, tee=True)

# Display results
model.x.display()
print(f"Objective value (Total Cost): {model.z.value}")

# Total cost calculation
total_cost = sum(model.x[i, j].value * (model.free_flow_time[i, j] + model.capacity[i, j] * model.x[i, j].value) for i, j in model.links)
print(f"Total Cost: {total_cost}")
