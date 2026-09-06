// ponytail: clean name input dialog with modal result validation
using System.Windows;
using System.Windows.Input;

namespace FaceSeeker.GUI.Views
{
    public partial class NameInputDialog : Window
    {
        public string EnteredName => NameBox.Text.Trim();

        public NameInputDialog(string initialName = "")
        {
            InitializeComponent();
            NameBox.Text = initialName;
            NameBox.Focus();
            NameBox.SelectAll();
        }

        private void OnOkClick(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(EnteredName))
            {
                MessageBox.Show("Please enter a valid person name.", "Validation", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            DialogResult = true;
            Close();
        }

        private void OnCancelClick(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

        private void OnKeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                OnOkClick(sender, e);
            }
            else if (e.Key == Key.Escape)
            {
                OnCancelClick(sender, e);
            }
        }
    }
}