import uvicorn

def main():
    print("Hello from backend!")


if __name__ == "__main__":
    # test again
    main()


    uvicorn.run(
        "app.main:app"
    )
