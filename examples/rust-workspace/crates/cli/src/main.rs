//! Prints the version of the command line and of the core it links.

fn main() {
    println!("demo-cli {} (core {})", env!("CARGO_PKG_VERSION"), demo_core::VERSION);
}
