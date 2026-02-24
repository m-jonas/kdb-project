def visualise_binary_file(filepath, bytes_to_read=64, chunk_size=16):

    try:
        with open(filepath, 'rb') as file:
            bytes_read = 0
            
            while bytes_read < bytes_to_read:
                chunk = file.read(chunk_size)
                if not chunk:
                    break

                binary_strings = [format(byte, '08b') for byte in chunk]

                print(' '.join(binary_strings))
                
                bytes_read += len(chunk)
                
    except FileNotFoundError:
        print(f"Error: Could not find the file at {filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

visualise_binary_file('data/01302019.NASDAQ_ITCH50', bytes_to_read=64, chunk_size=8)