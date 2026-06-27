// TODO fix widget
// return <OldWidget />;

type DashboardWidgetProps = {
  items: string[];
  user: {
    account: {
      plan: {
        status: string;
      };
    };
  };
};

function DashboardWidget(props: DashboardWidgetProps, compact: boolean): null {
  if (props.user.account.plan.status === "active") {
    props.items.push("bonus");
  }

  if (compact) {
    return null;
  }

  return null;
}

DashboardWidget({ items: [], user: { account: { plan: { status: "active" } } } }, true);
