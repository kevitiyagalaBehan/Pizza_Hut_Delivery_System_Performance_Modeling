import simpy
import random
import pandas as pd
import matplotlib.pyplot as plt

RANDOM_SEED = 42
SIM_TIME = 1000  # minutes (~16.5 peak hours)
ARRIVAL_RATE = 40  # orders per hour (peak)
LAMBDA = ARRIVAL_RATE / 60  # orders per minute

PREP_MEAN = 15  # kitchen prep time (min)
PREP_STD = 3

DELIVERY_MEAN = 12  # delivery travel time (min)
DELIVERY_STD = 4

SLA_TARGET = 30  # minutes


class PizzaHutSystem:
    def __init__(self, env, drivers):
        self.env = env
        self.drivers = simpy.Resource(env, capacity=drivers)

    def prepare_order(self):
        prep_time = max(5, random.gauss(PREP_MEAN, PREP_STD))
        yield self.env.timeout(prep_time)
        return prep_time

    def deliver_order(self):
        delivery_time = max(5, random.gauss(DELIVERY_MEAN, DELIVERY_STD))
        yield self.env.timeout(delivery_time)
        return delivery_time


def order(env, system, stats, order_id):
    arrival_time = env.now

    # Kitchen preparation
    yield from system.prepare_order()
    ready_time = env.now

    # Wait for available driver
    with system.drivers.request() as request:
        yield request
        driver_assigned_time = env.now

        wait_for_driver = driver_assigned_time - ready_time

        # Delivery
        delivery_time = yield from system.deliver_order()
        completion_time = env.now

        total_time = completion_time - arrival_time

        stats.append({
            "Order_ID": order_id,
            "Wait_For_Driver": wait_for_driver,
            "Total_Delivery_Time": total_time,
            "SLA_Met": total_time <= SLA_TARGET
        })


def order_generator(env, system, stats):
    order_id = 0
    while True:
        yield env.timeout(random.expovariate(LAMBDA))
        order_id += 1
        env.process(order(env, system, stats, order_id))


def run_simulation(num_drivers):
    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    stats = []

    system = PizzaHutSystem(env, num_drivers)
    env.process(order_generator(env, system, stats))
    env.run(until=SIM_TIME)

    df = pd.DataFrame(stats)

    return {
        "Drivers": num_drivers,
        "Avg_Wait_Time": round(df["Wait_For_Driver"].mean(), 2),
        "Avg_Total_Time": round(df["Total_Delivery_Time"].mean(), 2),
        "SLA_Compliance": round(df["SLA_Met"].mean() * 100, 2)
    }


results = []
driver_range = range(5, 21)

for d in driver_range:
    results.append(run_simulation(d))

results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))

plt.figure(figsize=(8, 5))
plt.plot(results_df["Drivers"], results_df["Avg_Total_Time"], marker='o')
plt.axhline(y=30, linestyle='--', color='red', label='SLA Target (30 min)')
plt.xlabel("Number of Drivers")
plt.ylabel("Average Delivery Time (min)")
plt.title("Driver Optimization vs Delivery Time")
plt.legend()
plt.grid(True)
plt.show()
