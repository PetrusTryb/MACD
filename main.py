from enum import Enum
import pandas as pd
import matplotlib.pyplot as plt

class MACD:
	stock_name = ''
	days = 1000
	data = None
 
	ema_12 = []
	ema_26 = []
	macd = []
	signal = []	
 
	operations = []
	class Operation(Enum):
		BUY = 1
		SELL = 2
		HOLD = 0
	instrument_balance = []
	money_balance = []
 
	def __init__(self,stock_name, days=1000):
		data = pd.read_csv(f'{stock_name}.csv').tail(days)
		print(data.columns)
		data = data[['<DATE>', '<CLOSE>']]
		data['<DATE>'] = pd.to_datetime(data['<DATE>'], format='%Y%m%d')
		data.set_index('<DATE>', inplace=True)
		self.stock_name = stock_name.upper()
		self.days = days
		self.data = data
		print(self.data)

	def print_data_graph(self):
		plt.plot(self.data['<CLOSE>'], color='black')
		plt.title(self.stock_name)
		plt.xlabel('Date')
		plt.ylabel('Price')
		plt.show()
  
	def ema(self, vector, period):
		alpha = 2 / (period + 1)
		ema = [vector[0]]
		for i in range(1, len(vector)):
			ema.append(alpha * vector[i] + (1 - alpha) * ema[i - 1])
		return ema
		
  
	def calculate_macd(self):
		self.ema_12 = self.ema(self.data['<CLOSE>'], 12)
		self.ema_26 = self.ema(self.data['<CLOSE>'], 26)
		assert len(self.ema_12) == len(self.ema_26)
		self.macd = list(map(lambda x, y: x - y, self.ema_12, self.ema_26))
		self.signal = self.ema(self.macd, 9)
  
	def plot_macd(self):
		plt.plot(self.data.index, self.macd, label='MACD', color='blue')
		plt.plot(self.data.index, self.signal, label='SIGNAL', color='darkorange')
		self.operations = []
		for i in range(0, len(self.macd)):
			if self.macd[i] > self.signal[i] and self.macd[i - 1] < self.signal[i - 1]:
				self.operations.append({"type": self.Operation.BUY, "price": self.data['<CLOSE>'].iloc[i]})
			elif self.macd[i] < self.signal[i] and self.macd[i - 1] > self.signal[i - 1]:
				self.operations.append({"type": self.Operation.SELL, "price": self.data['<CLOSE>'].iloc[i]})
			else:
				self.operations.append({"type": self.Operation.HOLD, "price": "N/A"})
		plt.scatter(self.data.index, [self.macd[i] if self.operations[i]["type"] == self.Operation.BUY else None for i in range(len(self.operations))], marker='^', color='green', label='BUY')
		plt.scatter(self.data.index, [self.macd[i] if self.operations[i]["type"] == self.Operation.SELL else None for i in range(len(self.operations))], marker='v', color='red', label='SELL')
		plt.title(f'MACD and Signal Line for {self.stock_name}')
		plt.xlabel('Date')
		plt.ylabel('Value')
		plt.legend()
		plt.show()
  
	def buy_sell(self, initial_balance=1000):
		self.instrument_balance = [initial_balance]
		self.money_balance = [0]
		print(f'Initial balance: {initial_balance*self.data["<CLOSE>"].iloc[0]} PLN')
		for i in range(1, len(self.operations)):
			type = self.operations[i]["type"]
			price = self.operations[i]["price"]
			if type == self.Operation.BUY and self.money_balance[i - 1] > 0:
				self.instrument_balance.append(self.money_balance[i - 1] // price)
				self.money_balance.append(self.money_balance[i - 1] - self.instrument_balance[i] * price)
			elif type == self.Operation.SELL and self.instrument_balance[i - 1] > 0:
				self.money_balance.append(self.money_balance[i - 1] + self.instrument_balance[i - 1] * price)
				self.instrument_balance.append(0)
			else:
				self.money_balance.append(self.money_balance[i - 1])
				self.instrument_balance.append(self.instrument_balance[i - 1])
		final = self.money_balance[-1] + self.instrument_balance[-1] * self.data["<CLOSE>"][-1]
		print(f'Final balance: {final} PLN')
		print(f'Profit: {final - initial_balance*self.data["<CLOSE>"].iloc[0]} PLN')
  
	def plot_balance(self):
		total_balance = [self.instrument_balance[i] * self.data["<CLOSE>"].iloc[i] + self.money_balance[i] for i in range(len(self.instrument_balance))]
		plt.plot(self.data.index, total_balance, label='Total balance', color='darkgreen')
		plt.scatter(self.data.index[0], total_balance[0], marker='o', color='red', label=f'Start: {total_balance[0].round(2)} PLN')
		plt.scatter(self.data.index[-1], total_balance[-1], marker='o', color='red', label=f'End: {total_balance[-1].round(2)} PLN')
		plt.title(f'Total wallet balance during {self.stock_name} trading')
		plt.xlabel('Date')
		plt.ylabel('Balance [PLN]')
		plt.legend()
		plt.show()
    

if __name__ == '__main__':
	macd_usd = MACD('usdpln', 1000)
	macd_usd.print_data_graph()
	macd_usd.calculate_macd()
	macd_usd.plot_macd()
	macd_usd.buy_sell()
	macd_usd.plot_balance()
	macd_nwg = MACD('nwg', 1000)
	macd_nwg.print_data_graph()
	macd_nwg.calculate_macd()
	macd_nwg.plot_macd()
	macd_nwg.buy_sell()
	macd_nwg.plot_balance()