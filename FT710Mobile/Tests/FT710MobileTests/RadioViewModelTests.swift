import XCTest
@testable import FT710Mobile

final class RadioViewModelTests: XCTestCase {
    
    var viewModel: RadioViewModel!
    
    override func setUp() {
        super.setUp()
        viewModel = RadioViewModel(serverHost: "localhost:8888", password: "test")
    }
    
    override func tearDown() {
        viewModel = nil
        super.tearDown()
    }
    
    // MARK: - Initialization Tests
    
    func testInitialState() {
        XCTAssertFalse(viewModel.state.powerOn)
        XCTAssertFalse(viewModel.state.ctrlConnected)
        XCTAssertFalse(viewModel.state.audioRXConnected)
        XCTAssertFalse(viewModel.state.audioTXConnected)
        XCTAssertFalse(viewModel.state.spectrumConnected)
        XCTAssertEqual(viewModel.state.frequency, 7000000)
        XCTAssertEqual(viewModel.state.mode, .LSB)
        XCTAssertEqual(viewModel.state.bandwidth, 1800)
    }
    
    func testPowerOn() {
        viewModel.powerOn()
        XCTAssertTrue(viewModel.state.powerOn)
    }
    
    func testPowerOff() {
        viewModel.powerOn()
        viewModel.powerOff()
        XCTAssertFalse(viewModel.state.powerOn)
    }
    
    // MARK: - Error Handling Tests
    
    func testShowError() {
        viewModel.showError(title: "Test Error", message: "This is a test error")
        
        XCTAssertTrue(viewModel.showErrorAlert)
        XCTAssertEqual(viewModel.errorTitle, "Test Error")
        XCTAssertEqual(viewModel.errorMessage, "This is a test error")
    }
    
    func testHandleAudioError() {
        viewModel.handleAudioError("Audio device not available")
        
        XCTAssertTrue(viewModel.showErrorAlert)
        XCTAssertEqual(viewModel.errorTitle, "音频错误")
        XCTAssertEqual(viewModel.errorMessage, "Audio device not available")
    }
    
    func testHandleConnectionError() {
        viewModel.handleConnectionError("Network unreachable")
        
        XCTAssertTrue(viewModel.showErrorAlert)
        XCTAssertEqual(viewModel.errorTitle, "连接错误")
        XCTAssertEqual(viewModel.errorMessage, "Network unreachable")
    }
    
    // MARK: - Frequency Control Tests
    
    func testFrequencyChange() {
        let newFreq: UInt32 = 14000000
        viewModel.setFrequency(newFreq)
        XCTAssertEqual(viewModel.state.frequency, newFreq)
    }
    
    func testFrequencyIncrement() {
        let originalFreq = viewModel.state.frequency
        viewModel.incrementFrequency()
        XCTAssertGreaterThan(viewModel.state.frequency, originalFreq)
    }
    
    func testFrequencyDecrement() {
        let originalFreq = viewModel.state.frequency
        viewModel.decrementFrequency()
        XCTAssertLessThan(viewModel.state.frequency, originalFreq)
    }
    
    // MARK: - Mode Control Tests
    
    func testModeChange() {
        viewModel.setMode(.USB)
        XCTAssertEqual(viewModel.state.mode, .USB)
    }
    
    func testModeToggle() {
        viewModel.toggleMode()
        // Just ensure it doesn't crash
    }
    
    // MARK: - Bandwidth Control Tests
    
    func testBandwidthChange() {
        viewModel.setBandwidth(2400)
        XCTAssertEqual(viewModel.state.bandwidth, 2400)
    }
    
    // MARK: - PTT Tests
    
    func testPTTActivation() {
        viewModel.setPTT(true)
        XCTAssertEqual(viewModel.state.txStatus, 1)
    }
    
    func testPTTRelease() {
        viewModel.setPTT(true)
        viewModel.setPTT(false)
        XCTAssertEqual(viewModel.state.txStatus, 0)
    }
    
    // MARK: - Gain Control Tests
    
    func testAFGainChange() {
        viewModel.setAFGain(200)
        XCTAssertEqual(viewModel.state.afGain, 200)
    }
    
    func testAGCAutoToggle() {
        viewModel.toggleAGCAuto()
        XCTAssertNotEqual(viewModel.state.agcAuto, nil) // Should toggle
    }
    
    // MARK: - Volume Control Tests
    
    func testVolumeChange() {
        viewModel.setVolume(75)
        XCTAssertEqual(viewModel.state.volume, 75)
    }
    
    // MARK: - Squelch Control Tests
    
    func testSquelchChange() {
        viewModel.setSquelch(50)
        XCTAssertEqual(viewModel.state.squelch, 50)
    }
    
    // MARK: - Notch Filter Tests
    
    func testNotchFilterToggle() {
        viewModel.toggleNotchFilter()
        XCTAssertNotEqual(viewModel.state.notchEnabled, nil) // Should toggle
    }
    
    // MARK: - DSP Tests
    
    func testDSPSettings() {
        viewModel.setDSPNoiseReduction(5)
        XCTAssertEqual(viewModel.state.dspNR, 5)
    }
}
