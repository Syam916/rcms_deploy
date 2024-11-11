# Step 1: Use an official Python image as the base image
FROM python:3.8-slim

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy the requirements file into the container
COPY requirements.txt /app/requirements.txt

# Step 4: Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of the application code to the container
COPY . /app

# Step 6: Copy the .env file to the container
# NOTE: Make sure to add .env to your .dockerignore if you don’t want it to be included in your image
COPY .env /app/.env

# Step 7: Expose the port that Flask will run on
EXPOSE 5000

# Step 8: Set environment variables for Flask
ENV FLASK_APP=app_2.py  
# Ensure this is your main application file
ENV FLASK_ENV=production

# Step 9: Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
