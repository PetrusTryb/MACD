'''
MACD - Piotr Trybisz
'''
from enum import Enum
import pandas as pd
import matplotlib.pyplot as plt
import os

class MACD:
	stock_name = 'NOT_INIT'
	days = 0
	data = None
 
	ema_12 = None
	ema_26 = None
	macd = None
	signal = None
 
	operations = None
	class Operation(Enum):
		BUY = 1
		SELL = 2
		HOLD = 0
	instrument_balance = None
	money_balance = None
	improve_delay = 0
 
	def __init__(self, stock_name, from_date=None, to_date=None, count=None):
		data = pd.read_csv(f'{stock_name}.csv')
		data['<DATE>'] = pd.to_datetime(data['<DATE>'], format='%Y%m%d')
		if count is not None:
			data = data.tail(count)
		else:
			data = data[(data['<DATE>'] >= pd.to_datetime(from_date, format='%Y-%m-%d')) & (data['<DATE>'] <= pd.to_datetime(to_date, format='%Y-%m-%d'))]
		data.set_index('<DATE>', inplace=True)
		self.data = pd.Series(data['<CLOSE>'])
		self.stock_name = stock_name.upper()
		self.days = len(self.data)
		print(f'Loaded {self.stock_name} data')
		#print(self.data)
		print("Date range: ", self.data.index[0], " - ", self.data.index[-1])

	def print_data_graph(self):
		plt.figure(figsize=(16, 6), dpi=300)
		plt.plot(self.data, color='black')
		plt.title(self.stock_name)
		plt.xlabel('Date')
		plt.ylabel('Closing price [PLN]')
		plt.savefig(f'plots/{self.stock_name}_graph.png', bbox_inches='tight')
		plt.close()
		print(f'Saved data graph at: plots/{self.stock_name}_graph.png')
  
	def ema(self, vector, period):
		alpha = 1 - (2 / (period + 1))
		ema = pd.Series(index=vector.index)
		for row in range(period, len(vector)):
			nominator = 0
			denominator = 0
			for i in range(0, period + 1):
				probe = vector.iloc[row - i]
				nominator += probe * (alpha ** i)
				denominator += alpha ** i
			ema.iloc[row] = nominator / denominator
		return ema
  
	def calculate_macd(self):
		self.ema_12 = self.ema(self.data, 12)
		self.ema_26 = self.ema(self.data, 26)
		self.macd = self.ema_12 - self.ema_26
		self.signal = self.ema(self.macd, 9)
		self.operations = pd.DataFrame(index=self.data.index, columns=['type', 'macd_value', 'prev_op', 'price', 'profit', 'disabled'])
		self.operations['type'] = self.Operation.HOLD
		has_sell = False
		prev_buy = None
		prev_sell = None
		for i in range(0, self.days):
			if self.macd.iloc[i] > self.signal.iloc[i] and self.macd.iloc[i - 1] < self.signal.iloc[i - 1] and has_sell:
				self.operations.iloc[i] = {"type": self.Operation.BUY, "macd_value": self.signal.iloc[i], "price": self.data.iloc[i], "prev_op": prev_sell}
				prev_buy = self.operations.index[i]
			elif self.macd.iloc[i] < self.signal.iloc[i] and self.macd.iloc[i - 1] > self.signal.iloc[i - 1]:
				self.operations.iloc[i] = {"type": self.Operation.SELL, "macd_value": self.signal.iloc[i], "price": self.data.iloc[i], "prev_op": prev_buy}
				prev_sell = self.operations.index[i]
				has_sell = True
    
	def improve_macd(self, delay=7):
		self.improve_delay = delay
		self.operations['disabled'] = False
		active_operations = self.operations[(self.operations["type"] != self.Operation.HOLD) & (self.operations["disabled"] != True)].copy()
		for i in range(2, len(active_operations)):
			disabled = active_operations.iloc[i]["disabled"] == True
			if disabled:
				continue
			type = active_operations.iloc[i]["type"]
			dat = active_operations.index[i]
			prev = active_operations.iloc[i]["prev_op"]
			if (dat - prev).days < delay:
				active_operations.loc[dat,"disabled"] = True
				next = active_operations[(active_operations["type"] != type) & (active_operations.index > dat)]
				if len(next) > 0:
					next = next.index[0]
				else:
					continue
				active_operations.loc[next,"disabled"] = True
		self.operations.update(active_operations)
			
  
	def plot_macd(self):
		macd = self.macd
		signal = self.signal
		operations = self.operations
		buy_operations = operations[(operations["type"] == self.Operation.BUY)&(operations["disabled"] != True)]
		sell_operations = operations[(operations["type"] == self.Operation.SELL)&(operations["disabled"] != True)]
		buy_disabled = operations[(operations["type"] == self.Operation.BUY)&(operations["disabled"] == True)]
		sell_disabled = operations[(operations["type"] == self.Operation.SELL)&(operations["disabled"] == True)]
		plt.figure(figsize=(16, 6), dpi=200)
		plt.plot(macd.index, macd, label='MACD', color='blue')
		plt.plot(signal.index, signal, label='SIGNAL', color='darkorange')
		plt.scatter(buy_operations.index, buy_operations["macd_value"], marker='^', color='green', label='BUY')
		plt.scatter(sell_operations.index, sell_operations["macd_value"], marker='v', color='red', label='SELL')
		plt.scatter(buy_disabled.index, buy_disabled["macd_value"], marker='^', color='lightgreen', label='BUY_DISABLED')
		plt.scatter(sell_disabled.index, sell_disabled["macd_value"], marker='v', color='lightcoral', label='SELL_DISABLED')
		plt.title(f'MACD and Signal Line for {self.stock_name} (ΔT={self.improve_delay})')
		plt.xlabel('Date')
		plt.ylabel('Value')
		plt.legend()
		filename = f'plots/{self.stock_name}_macd_dT{self.improve_delay}.png'
		plt.savefig(filename, bbox_inches='tight')
		plt.close()
		print(f'Saved MACD plot at: {filename}')
  
	def buy_sell(self, initial_balance=1000, problems_detection = False):
		self.instrument_balance = pd.Series(index=self.data.index)
		self.money_balance = pd.Series(index=self.data.index)
		self.instrument_balance.iloc[0] = initial_balance
		self.money_balance.iloc[0] = 0
		print(f'Initial balance: {initial_balance*self.data.iloc[0]} PLN')
		last_price = self.data.iloc[0]*initial_balance
		active_operations = self.operations[(self.operations["type"] != self.Operation.HOLD) & (self.operations["disabled"] != True)].copy()
		for i in range(0, len(active_operations)):
			dat = active_operations.index[i]
			type = active_operations.iloc[i]["type"]
			price = active_operations.iloc[i]["price"]
			if type == self.Operation.BUY and self.money_balance[self.money_balance.last_valid_index()] > 0:
				self.instrument_balance[dat] = self.money_balance[self.money_balance.last_valid_index()] // price
				self.money_balance[dat] = self.money_balance[self.money_balance.last_valid_index()] - self.instrument_balance[dat] * price
				last_price = price * self.instrument_balance[dat]
			elif type == self.Operation.SELL and self.instrument_balance[self.instrument_balance.last_valid_index()] > 0:
				self.money_balance[dat] = self.money_balance[self.money_balance.last_valid_index()] + self.instrument_balance[self.instrument_balance.last_valid_index()] * price
				self.instrument_balance[dat] = 0
				profit = self.money_balance[dat] - last_price
				active_operations.loc[dat,"profit"] = profit
		self.instrument_balance.ffill(inplace=True)
		self.money_balance.ffill(inplace=True)
		final = self.money_balance.iloc[-1] + self.instrument_balance.iloc[-1] * self.data.iloc[-1]
		print(f'Final balance: {final:.2f} PLN')
		print(f'Profit: {final - initial_balance*self.data.iloc[0]:.2f} PLN')
		sell_operations = active_operations[active_operations["type"] == self.Operation.SELL]
		with open(f'logs/{self.stock_name}_buysell_dT{self.improve_delay}.csv', 'w') as f:
			f.write('"No.", "Buy date", "Buy price", "Sell date", "Sell price", "Profit"\n')
			for i in range(len(sell_operations)):
				if i==0:
					buy_price = self.data.iloc[0]
					buy_date = self.data.index[0]
				else:
					buy_price = active_operations[active_operations["type"] == self.Operation.BUY].iloc[i-1]["price"]
					buy_date = active_operations[active_operations["type"] == self.Operation.BUY].index[i-1]
				f.write(f'"{i}", "{str(buy_date).split(" ")[0]}", "{buy_price:.2f}", "{str(sell_operations.index[i]).split(" ")[0]}", "{sell_operations.iloc[i]["price"]:.2f}", "{sell_operations.iloc[i]["profit"]:.2f} PLN", \n')
		print(f'Saved trading log at: logs/{self.stock_name}_buysell_dT{self.improve_delay}.csv')
		if problems_detection:
			wrong_operations = active_operations[active_operations["profit"] < 0]
			print(f'Problems detectedL {len(wrong_operations)}')
			worst_operations = wrong_operations.sort_values(by='profit', ascending=True)
			for i in range(5):
				self.plot_fragment(worst_operations.index[i], 30)
		return final - initial_balance*self.data.iloc[0]

	def plot_balance(self):
		operations = self.operations
		buy_operations = operations[(operations["type"] == self.Operation.BUY)&(operations["disabled"] != True)]
		sell_operations = operations[(operations["type"] == self.Operation.SELL)&(operations["disabled"] != True)]
		buy_disabled = operations[(operations["type"] == self.Operation.BUY)&(operations["disabled"] == True)]
		sell_disabled = operations[(operations["type"] == self.Operation.SELL)&(operations["disabled"] == True)]
		plt.figure(figsize=(16, 6), dpi=200)
		plt.plot(self.data.index, self.data, label='Closing price [PLN]')
		plt.scatter(buy_operations.index, buy_operations['price'], marker='^', color='green', label='BUY')
		plt.scatter(sell_operations.index, sell_operations['price'], marker='v', color='red', label='SELL')
		plt.scatter(buy_disabled.index, buy_disabled['price'], marker='^', color='lightgreen', label='BUY_DISABLED')
		plt.scatter(sell_disabled.index, sell_disabled['price'], marker='v', color='lightcoral', label='SELL_DISABLED')
		plt.title(f'Simulation of {self.stock_name} trading (ΔT={self.improve_delay})')
		plt.xlabel('Date')
		plt.ylabel('Closing price [PLN]')
		plt.legend()
		filename = f'plots/{self.stock_name}_buysell_dT{self.improve_delay}.png'
		plt.savefig(filename, bbox_inches='tight')
		print(f'Saved trading plot at: {filename}')
		plt.close()

	def plot_fragment(self, around, margin):
		date_from = pd.to_datetime(around, format='%Y-%m-%d') - pd.DateOffset(days=margin)
		date_to = pd.to_datetime(around, format='%Y-%m-%d') + pd.DateOffset(days=margin)
		data_fragment = self.data[(self.data.index >= date_from) & (self.data.index <= date_to)]
		operations = self.operations[(self.operations.index >= date_from) & (self.operations.index <= date_to)]
		buy_operations = operations[(operations["type"] == self.Operation.BUY)&(operations["disabled"] != True)]
		sell_operations = operations[(operations["type"] == self.Operation.SELL)&(operations["disabled"] != True)]
		buy_disabled = operations[(operations["type"] == self.Operation.BUY)&(operations["disabled"] == True)]
		sell_disabled = operations[(operations["type"] == self.Operation.SELL)&(operations["disabled"] == True)]
		plt.figure(figsize=(16, 6), dpi=200)
		plt.plot(data_fragment.index, data_fragment, label='Closing price [PLN]')
		plt.scatter(buy_operations.index, buy_operations['price'], marker='^', color='green', label='BUY')
		plt.scatter(sell_operations.index, sell_operations['price'], marker='v', color='red', label='SELL')
		plt.scatter(buy_disabled.index, buy_disabled['price'], marker='^', color='lightgreen', label='BUY_DISABLED')
		plt.scatter(sell_disabled.index, sell_disabled['price'], marker='v', color='lightcoral', label='SELL_DISABLED')
		plt.title(f'Simulation of {self.stock_name} trading')
		plt.xlabel('Date')
		plt.ylabel('Closing price [PLN]')
		plt.legend()
		filename = f'plots/{self.stock_name}_buysell_{str(date_from).split(" ")[0]}_{str(date_to).split(" ")[0]}_dT{self.improve_delay}.png'
		plt.savefig(filename, bbox_inches='tight')
		print(f'Saved trading plot at: {filename}.png')
		plt.close()

if __name__ == '__main__':
	os.makedirs('plots', exist_ok=True)
	os.makedirs('logs', exist_ok=True)
	macd_usd = MACD('usdpln', count=1000)
	macd_usd.print_data_graph()
	macd_usd.calculate_macd()
	macd_usd.plot_macd()
	macd_usd.buy_sell(problems_detection=True)
	macd_usd.plot_balance()
 
	dT_results = []
	for deltaT in range(0, 30, 3):
		macd_usd.improve_macd(deltaT)
		macd_usd.plot_macd()
		dT_results.append(macd_usd.buy_sell())
		macd_usd.plot_balance()

	for i in range(len(dT_results)):
		print(f'"{i*3}", "{dT_results[i]:.2f} PLN"')
	
	macd_nwg = MACD('nwg', count=1000)
	macd_nwg.print_data_graph()
	macd_nwg.calculate_macd()
	macd_nwg.plot_macd()
	macd_nwg.buy_sell(problems_detection=True)
	macd_nwg.plot_balance()
 
	dT_results = []
	for deltaT in range(0, 30, 3):
		macd_nwg.improve_macd(deltaT)
		macd_nwg.plot_macd()
		dT_results.append(macd_nwg.buy_sell())
		macd_nwg.plot_balance()
  
	for i in range(len(dT_results)):
		print(f'"{i*3}", "{dT_results[i]:.2f} PLN"')
	