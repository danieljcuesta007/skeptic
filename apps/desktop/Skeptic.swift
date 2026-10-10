import AppKit
import WebKit

final class App: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    var window: NSWindow!
    var process: Process?
    var lease: Pipe?
    var origin: URL?
    var stopping = false
    var web: WKWebView!
    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x:0,y:0,width:1120,height:780), styleMask:[.titled,.closable,.miniaturizable,.resizable], backing:.buffered, defer:false)
        window.title = "Skeptic"
        window.minSize = NSSize(width:680,height:560)
        window.center()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        config.preferences.javaScriptCanOpenWindowsAutomatically = false
        web = WKWebView(frame:window.contentView!.bounds, configuration:config)
        web.autoresizingMask = [.width,.height]
        web.navigationDelegate = self
        window.contentView = web
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps:true)
        let menu = NSMenu();let item = NSMenuItem();menu.addItem(item)
        let appMenu = NSMenu();appMenu.addItem(withTitle:"Quit Skeptic",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q");item.submenu=appMenu
        let editItem=NSMenuItem();menu.addItem(editItem);let edit=NSMenu(title:"Edit");editItem.submenu=edit
        for (title, selector, key) in [("Copy","copy:","c"),("Paste","paste:","v"),("Select All","selectAll:","a")] {edit.addItem(withTitle:title,action:NSSelectorFromString(selector),keyEquivalent:key)}
        NSApp.mainMenu=menu
        guard let resources=Bundle.main.resourceURL else {fail();return}
        let p=Process();let input=Pipe();let output=Pipe();let errors=Pipe()
        p.executableURL=URL(fileURLWithPath:"/usr/bin/python3")
        p.arguments=["-B",resources.appendingPathComponent("runtime/apps/desktop/backend.py").path]
        p.standardInput=input;p.standardOutput=output;p.standardError=errors
        process=p;lease=input
        p.terminationHandler={ [weak self] _ in DispatchQueue.main.async { if self?.stopping == false {self?.fail()} } }
        do {try p.run()} catch {fail();return}
        DispatchQueue.global().async { [weak self] in
            var bytes=Data()
            while bytes.count<1024 {
                let next=output.fileHandleForReading.readData(ofLength:1)
                if next.isEmpty || next == Data([10]) {break}
                bytes.append(next)
            }
            guard let object=try? JSONSerialization.jsonObject(with:bytes) as? [String:String], let value=object["origin"], let url=URL(string:value), url.scheme=="http",url.host=="127.0.0.1",url.port != nil,url.path.isEmpty else {DispatchQueue.main.async {self?.fail()};return}
            DispatchQueue.main.async {self?.origin=url;self?.web.load(URLRequest(url:url))}
        }
    }
    func fail() {
        let alert=NSAlert();alert.messageText="Skeptic could not start"
        alert.informativeText="Close any other Skeptic app and try again. This development app requires macOS Python 3 and permission to bind a private loopback server. No project or session files were changed."
        alert.runModal();NSApp.terminate(nil)
    }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy)->Void) {
        guard let url=navigationAction.request.url,let allowed=origin,url.scheme==allowed.scheme,url.host==allowed.host,url.port==allowed.port else {decisionHandler(.cancel);return}
        decisionHandler(.allow)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender:NSApplication)->Bool {true}
    func applicationWillTerminate(_ notification:Notification) {
        stopping = true
        try? lease?.fileHandleForWriting.close()
        if let p=process,p.isRunning {
            let deadline=Date().addingTimeInterval(3)
            while p.isRunning && Date()<deadline {Thread.sleep(forTimeInterval:0.05)}
            if p.isRunning {p.terminate()}
        }
    }
}
let application=NSApplication.shared
application.setActivationPolicy(.regular)
let delegate=App();application.delegate=delegate;application.run()
