#!/usr/bin/python
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from datetime import timedelta, datetime

predict_range = 200
s_0=99998
i_0=2
r_0=0
class Learner(object):
    def __init__(self, loss, predict_range, s_0, i_0, r_0):
        self.loss = loss
        self.predict_range = predict_range
        self.s_0 = s_0
        self.i_0 = i_0
        self.r_0 = r_0
    def load_confirmed(self):
      df = pd.read_csv('02_SZ_DailyCases.csv')
      df.set_index(["Date"], inplace=True)
      dff=df["cummulative confirmed cases"]
      print(dff.T)
      return dff.T

    def load_recovered(self):
        df = pd.read_csv('02_SZ_DailyCases.csv')
        df.set_index(["Date"], inplace=True)
        dff = df["cummulative cured cases"]
        print(dff.T)
        return dff.T

    def load_dead(self):
        df = pd.read_csv('02_SZ_DailyCases.csv')
        df.set_index(["Date"], inplace=True)
        dff = df["cummulative dead cases"]
        print(dff.T)
        return dff.T

    def extend_index(self, index, new_size):
        values = index.values
        current = datetime.strptime(index[-1], '%m/%d/%y')
        while len(values) < new_size:
            current = current + timedelta(days=1)
            values = np.append(values, datetime.strftime(current, '%m/%d/%y'))
        return values

    def predict(self, beta, gamma, data, recovered, death, s_0, i_0, r_0):
        new_index = self.extend_index(data.index, self.predict_range)
        size = len(new_index)

        def SIR(t, y):
            S = y[0]
            I = y[1]
            R = y[2]
            return [-beta * S * I, beta * S * I - gamma * I, gamma * I]

        extended_actual = np.concatenate((data.values, [None] * (size - len(data.values))))
        extended_recovered = np.concatenate((recovered.values, [None] * (size - len(recovered.values))))
        extended_death = np.concatenate((death.values, [None] * (size - len(death.values))))
        return new_index, extended_actual, extended_recovered, extended_death, solve_ivp(SIR, [0, size],
                                                                                         [s_0, i_0, r_0],
                                                                                         t_eval=np.arange(0, size, 1))

    def train(self):
        recovered = self.load_recovered()
        death = self.load_dead()
        data = (self.load_confirmed() - recovered - death)

        optimal = minimize(loss, [0.001, 0.001], args=(data, recovered, self.s_0, self.i_0, self.r_0),
                           method='L-BFGS-B', bounds=[(0.00000001, 0.4), (0.00000001, 0.4)])
        print(optimal)
        beta, gamma = optimal.x
        new_index, extended_actual, extended_recovered, extended_death, prediction = self.predict(beta, gamma, data,
                                                                                                  recovered, death,

                                                                                                  self.s_0, self.i_0,
                                                                                                  self.r_0)
        df = pd.DataFrame(
            {'Infected data': extended_actual, 'Recovered data': extended_recovered, 'Death data': extended_death,
             'Susceptible': prediction.y[0], 'Infected': prediction.y[1], 'Recovered': prediction.y[2]},
            index=new_index)
        fig, ax = plt.subplots(figsize=(15, 10))
        df.to_csv("result_SIR.csv")
        #ax.set_title(self.country)
        df.plot(ax=ax)
        print(f" beta={beta:.8f}, gamma={gamma:.8f}, r_0:{(beta / gamma):.8f}")
        fig.savefig("result.png")


def loss(point, data, recovered, s_0, i_0, r_0):
    size = len(data)
    beta, gamma = point

    def SIR(t, y):
        S = y[0]
        I = y[1]
        R = y[2]
        return [-beta * S * I, beta * S * I - gamma * I, gamma * I]

    solution = solve_ivp(SIR, [0, size], [s_0, i_0, r_0], t_eval=np.arange(0, size, 1), vectorized=True)
    l1 = np.sqrt(np.mean((solution.y[1] - data) ** 2))
    l2 = np.sqrt(np.mean((solution.y[2] - recovered) ** 2))
    alpha = 0.1
    return alpha * l1 + (1 - alpha) * l2


def main():
    learner = Learner(loss, predict_range, s_0, i_0, r_0)
    learner.train()


if __name__ == '__main__':
    main()