// ponytail: clean match result row control
using System.Windows;
using System.Windows.Controls;
using FaceSeeker.GUI.ViewModels;

namespace FaceSeeker.GUI.Controls
{
    public partial class MatchResultRow : UserControl
    {
        public static readonly DependencyProperty ResultProperty =
            DependencyProperty.Register(nameof(Result), typeof(MatchResultViewModel), typeof(MatchResultRow), new PropertyMetadata(null, (d, e) =>
            {
                if (d is MatchResultRow row && e.NewValue is MatchResultViewModel vm)
                {
                    row.DataContext = vm;
                }
            }));

        public MatchResultViewModel? Result
        {
            get => (MatchResultViewModel?)GetValue(ResultProperty);
            set => SetValue(ResultProperty, value);
        }

        public MatchResultRow()
        {
            InitializeComponent();
        }
    }
}