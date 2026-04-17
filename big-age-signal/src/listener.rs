use std::os::unix::net::UnixListener;
use std::io::{Read, BufRead, BufReader};
use std::process::Command;
use std::fs::{set_permissions, Permissions};
use std::os::unix::fs::PermissionsExt;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let socket_path = format!(
        "{}/big-parental.sock",
        std::env::var("XDG_RUNTIME_DIR").unwrap()
    );

    let _ = std::fs::remove_file(&socket_path);
    let listener = UnixListener::bind(&socket_path).unwrap_or_else(|err| panic!("Erro ao criar socket: {}", err));
    set_permissions(&socket_path, Permissions::from_mode(0o777))?;

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                let mut reader = BufReader::new(stream);
                let mut buf = String::new();

                if reader.read_line(&mut buf).is_ok() {
                    let parts: Vec<&str> = buf.trim().split('|').collect();

                    if parts.len() == 2 {
                        let _ = Command::new("notify-send")
                            .args(["-a", "Parental Control"])
                            .arg(parts[0])
                            .arg(parts[1])
                            .output();
                    }
                } else {
                    eprintln!("Erro ao ler dados do stream.");
                }
            }
            Err(e) => {
                eprintln!("Erro na conexão do stream: {}", e);
            }
        }
    }

    Ok(())
}