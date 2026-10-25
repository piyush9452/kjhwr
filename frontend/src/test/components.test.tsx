import { fireEvent, render, screen } from '@testing-library/react';
import { DEFAULT_QUERY } from '../api';
import { Chart } from '../components/Chart';
import { Controls } from '../components/Controls';
import { MetricCard } from '../components/MetricCard';

describe('MetricCard', () => {
  it('renders label, value and hint', () => {
    render(<MetricCard label="MAE" value="2,039 MW" hint="18% of mean actual" />);
    expect(screen.getByRole('group', { name: 'MAE' })).toHaveTextContent('2,039 MW');
    expect(screen.getByText('18% of mean actual')).toBeInTheDocument();
  });
});

describe('Controls', () => {
  it('switches to horizon mode and exposes the slider', () => {
    const onChange = vi.fn();
    const { rerender } = render(<Controls query={DEFAULT_QUERY} onChange={onChange} />);
    fireEvent.click(screen.getByRole('radio', { name: 'Fixed horizon' }));
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT_QUERY, mode: 'horizon' });

    rerender(<Controls query={{ ...DEFAULT_QUERY, mode: 'horizon' }} onChange={onChange} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '12' } });
    expect(onChange).toHaveBeenLastCalledWith({ ...DEFAULT_QUERY, mode: 'horizon', horizon: 12 });
  });

  it('drags the end date forward when start moves past it', () => {
    const onChange = vi.fn();
    render(<Controls query={DEFAULT_QUERY} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('Delivery date'), { target: { value: '2026-01-20' } });
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_QUERY,
      start: '2026-01-20',
      end: '2026-01-20',
    });
  });
});

describe('Chart states', () => {
  const child = <div />;
  it('shows error, loading and empty states', () => {
    const { rerender } = render(
      <Chart title="T" loading={false} error="500: boom" empty={false}>
        {child}
      </Chart>,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('500: boom');
    rerender(
      <Chart title="T" loading error={null} empty={false}>
        {child}
      </Chart>,
    );
    expect(screen.getByText('Loading…')).toBeInTheDocument();
    rerender(
      <Chart title="T" loading={false} error={null} empty>
        {child}
      </Chart>,
    );
    expect(screen.getByText('No data for this selection.')).toBeInTheDocument();
  });
});
