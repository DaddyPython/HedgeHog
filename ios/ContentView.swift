import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var viewModel: TradingViewModel

    var body: some View {
        ZStack {
            DigitalRainBackground()
            VStack(spacing: 20) {
                Text("🐗 Hedge Hog // Matrix Terminal")
                    .font(.custom("ShareTechMono-Regular", size: 24))
                    .foregroundColor(.matrixGreen)

                Picker("Symbol", selection: $viewModel.selectedSymbol) {
                    ForEach(viewModel.symbols, id: \.self) { symbol in
                        Text(symbol).tag(symbol)
                    }
                }
                .pickerStyle(.wheel)
                .frame(height: 120)
                .clipped()

                HStack {
                    Text("Size")
                    Spacer()
                    Text("\(Int(viewModel.size)) USDT")
                }
                Slider(value: $viewModel.size, in: 1...100, step: 1)
                    .tint(.matrixGreen)

                VStack(alignment: .leading) {
                    Text("Take Profit: \(Int(viewModel.takeProfit * 100))%")
                    Slider(value: $viewModel.takeProfit, in: 1.01...1.5)
                        .tint(.matrixGreen)
                }

                VStack(alignment: .leading) {
                    Text("Stop Loss: \(Int(viewModel.stopLoss * 100))%")
                    Slider(value: $viewModel.stopLoss, in: 0.5...0.99)
                        .tint(.matrixGreen)
                }

                Button(action: viewModel.executeTrade) {
                    Text("EXECUTE TRADE")
                        .font(.headline)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.matrixGreen.opacity(0.2))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.matrixGreen, lineWidth: 2)
                                .shadow(color: Color.matrixGreen, radius: 8)
                        )
                }

                Button(action: viewModel.cancelAll) {
                    Text("STOP ALL TRADES")
                        .font(.headline)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.matrixRed.opacity(0.2))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.matrixRed, lineWidth: 2)
                                .shadow(color: Color.matrixRed, radius: 8)
                        )
                }

                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(viewModel.logs) { log in
                            Text(log.message)
                                .font(.system(size: 12, weight: .medium, design: .monospaced))
                                .foregroundColor(log.level.color)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
                .frame(height: 220)
                .background(Color.black.opacity(0.6))
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .padding()
        }
        .task {
            await viewModel.refreshSymbols()
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView().environmentObject(TradingViewModel())
    }
}
