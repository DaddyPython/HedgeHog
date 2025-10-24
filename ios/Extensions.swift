import SwiftUI

extension Color {
    static let matrixGreen = Color(red: 0, green: 1, blue: 0.255)
    static let matrixRed = Color(red: 1, green: 0, blue: 0.3)
}

struct DigitalRainBackground: View {
    @State private var offset: CGFloat = 0

    var body: some View {
        LinearGradient(
            gradient: Gradient(colors: [Color.black, Color.black.opacity(0.7)]),
            startPoint: .top,
            endPoint: .bottom
        )
        .overlay(
            GeometryReader { geometry in
                Rectangle()
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [.clear, Color.matrixGreen.opacity(0.2), .clear]),
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .blendMode(.screen)
                    .offset(y: offset)
                    .animation(
                        .linear(duration: 4)
                            .repeatForever(autoreverses: false),
                        value: offset
                    )
                    .onAppear {
                        offset = geometry.size.height
                    }
            }
        )
        .ignoresSafeArea()
    }
}

struct LogEntry: Identifiable {
    let id = UUID()
    let level: LogLevel
    let message: String
}

enum LogLevel: String {
    case info
    case warning
    case error

    var color: Color {
        switch self {
        case .info:
            return .matrixGreen
        case .warning:
            return .yellow
        case .error:
            return .matrixRed
        }
    }
}
