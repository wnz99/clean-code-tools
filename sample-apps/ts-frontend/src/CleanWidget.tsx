const MAX_VISIBLE_ITEMS = 5;

interface DashboardWidgetProps {
  readonly items: readonly string[];
  readonly shouldShowEmptyState: boolean;
}

function visibleItems(items: readonly string[]): readonly string[] {
  return items.slice(0, MAX_VISIBLE_ITEMS);
}

export function DashboardWidget({ items, shouldShowEmptyState }: DashboardWidgetProps): string {
  if (items.length === 0 && shouldShowEmptyState) {
    return "No items";
  }

  return visibleItems(items).join(", ");
}
