import socket
import json

# Configuration - must match the bird_detector.py settings
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

def main():
    # 1. Initialize the UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 2. Bind to the local address and port
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"Could not bind to {UDP_IP}:{UDP_PORT}. Error: {e}")
        return
    
    print(f"UDP Receiver Example started. Listening on {UDP_IP}:{UDP_PORT}...")
    print("Waiting for detections from the OAK-D Lite...\n")

    try:
        while True:
            # 3. Listen for incoming data (4096 is the buffer size)
            data, addr = sock.recvfrom(4096)
            
            try:
                # 4. Decode the byte string and parse the JSON payload
                payload = json.loads(data.decode('utf-8'))
                
                # 5. Handle the data
                if "status" in payload:
                    # This is a system heartbeat
                    print(f"[SYSTEM] Heartbeat received. Status: {payload.get('status')}")
                else:
                    # This is a real detection tracklet
                    label = payload.get("label", "Unknown")
                    obj_id = payload.get("id", "?")
                    spatial = payload.get("spatial", {})
                    
                    x = spatial.get("x_mm", 0)
                    y = spatial.get("y_mm", 0)
                    z = spatial.get("z_mm", 0)

                    print(f"[NEW DATA] Detected {label.upper()} (Track ID: {obj_id})")
                    print(f"  Location: X={x}mm, Y={y}mm, Z={z}mm")
                    print("-" * 40)

            except json.JSONDecodeError:
                print(f"Received invalid JSON from {addr}")
            except Exception as e:
                print(f"Error processing message: {e}")

    except KeyboardInterrupt:
        print("\nReceiver stopped by user.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
