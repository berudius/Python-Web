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
    #     except Exception as e:
    #         print(e)
    # except Exception as e:
    #     print(e)