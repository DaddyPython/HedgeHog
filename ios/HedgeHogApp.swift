import SwiftUI

@main
struct HedgeHogApp: App {
    @StateObject private var viewModel = TradingViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
        }
    }
}
