import Combine
import Foundation
import SwiftUI

@MainActor
final class TradingViewModel: ObservableObject {
    @Published var symbols: [String] = []
    @Published var selectedSymbol: String = ""
    @Published var size: Double = 1
    @Published var takeProfit: Double = 1.11
    @Published var stopLoss: Double = 0.9
    @Published var logs: [LogEntry] = []

    private let api = HedgeHogAPI()
    private var timer: AnyCancellable?

    init() {
        timer = Timer.publish(every: 15, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                Task {
                    await self?.refreshSymbols()
                }
            }
    }

    func refreshSymbols() async {
        do {
            let symbols = try await api.fetchSymbols()
            self.symbols = symbols
            if selectedSymbol.isEmpty, let first = symbols.first {
                selectedSymbol = first
            }
            appendLog(level: .info, message: "Loaded symbols: \(symbols.count)")
        } catch {
            appendLog(level: .error, message: "Symbol refresh failed: \(error.localizedDescription)")
        }
    }

    func executeTrade() {
        Task {
            do {
                try await api.execute(
                    symbol: selectedSymbol,
                    size: size,
                    takeProfit: takeProfit,
                    stopLoss: stopLoss
                )
                appendLog(level: .info, message: "Executed dual orders for \(selectedSymbol)")
            } catch {
                appendLog(level: .error, message: "Execute failed: \(error.localizedDescription)")
            }
        }
    }

    func cancelAll() {
        Task {
            do {
                try await api.cancel(symbol: selectedSymbol)
                appendLog(level: .warning, message: "Cancel requested for \(selectedSymbol)")
            } catch {
                appendLog(level: .error, message: "Cancel failed: \(error.localizedDescription)")
            }
        }
    }

    private func appendLog(level: LogLevel, message: String) {
        withAnimation {
            logs.append(LogEntry(level: level, message: message))
            logs = logs.suffix(200)
        }
    }
}

struct HedgeHogAPI {
    private let baseURL = URL(string: "http://localhost:5000/api")!

    func fetchSymbols() async throws -> [String] {
        let url = baseURL.appendingPathComponent("symbols")
        let (data, _) = try await URLSession.shared.data(from: url)
        let response = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        if let error = response?["error"] as? String {
            throw APIError.server(error)
        }
        return response?["symbols"] as? [String] ?? []
    }

    func execute(symbol: String, size: Double, takeProfit: Double, stopLoss: Double) async throws {
        let url = baseURL.appendingPathComponent("execute")
        let payload: [String: Any] = [
            "symbol": symbol,
            "size": size,
            "takeProfit": takeProfit,
            "stopLoss": stopLoss,
        ]
        let data = try JSONSerialization.data(withJSONObject: payload)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = data
        let (responseData, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: responseData)
    }

    func cancel(symbol: String) async throws {
        let url = baseURL.appendingPathComponent("cancel")
        let payload: [String: Any] = ["symbol": symbol]
        let data = try JSONSerialization.data(withJSONObject: payload)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = data
        let (responseData, response) = try await URLSession.shared.data(for: request)
        try validate(response: response, data: responseData)
    }

    private func validate(response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        if (200..<300).contains(http.statusCode) {
            return
        }
        if let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let error = object["error"] as? String {
            throw APIError.server(error)
        }
        throw APIError.invalidResponse
    }
}

enum APIError: LocalizedError {
    case server(String)
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .server(let message):
            return message
        case .invalidResponse:
            return "Unexpected response from server"
        }
    }
}
