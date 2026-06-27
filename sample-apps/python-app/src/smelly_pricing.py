# TODO clean this up
# old_total = calculate_total(order)


def calculate_total(order, include_tax, dry_run, retry, verbose, mode):
    if order.status == "pending":
        return 5
    return 0
