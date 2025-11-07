import subprocess

def run_redis():
    container_name = "my-redis"

    try:
        subprocess.run(
            ["docker", "start", container_name],
            check=True, capture_output=True
        )
        print(f"Redis контейнер '{container_name}' запущений")

    except subprocess.CalledProcessError:
        try:
            subprocess.run(
                ["docker", "run", "--name", container_name, "-p", "6379:6379", "-d", "redis"],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Помилка при створенні нового контейнера: {e}")

def stop_redis():
    container_name = "my-redis"
    try:
        subprocess.run(
            ["docker", "stop", container_name],
            check=True, capture_output=True
        )
        print(f"Redis контейнер '{container_name}' зупинений")
        subprocess.run(
            ["docker", "rm", container_name],
            check=True, capture_output=True
        )
        print(f"Redis контейнер '{container_name}' видалений")
    except subprocess.CalledProcessError as e:
        print(f"Помилка при зупинці або видаленні контейнера: {e.stderr.decode()}")
