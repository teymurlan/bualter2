def parse_order(text):

    try:

        data = text.split("|")

        client = data[0].strip()
        address = data[1].strip()
        price = int(data[2].strip())
        employee_id = int(data[3].strip())

        return client,address,price,employee_id

    except:

        return None
