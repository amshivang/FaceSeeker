// ponytail: clean target face card control with remove action
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using FaceSeeker.GUI.Models;

namespace FaceSeeker.GUI.Controls
{
    public partial class TargetFaceCard : UserControl
    {
        public static readonly DependencyProperty PersonNameProperty =
            DependencyProperty.Register(nameof(PersonName), typeof(string), typeof(TargetFaceCard), new PropertyMetadata("", (d, e) =>
            {
                if (d is TargetFaceCard card) card.NameText.Text = e.NewValue as string ?? "";
            }));

        public static readonly DependencyProperty ImagePathProperty =
            DependencyProperty.Register(nameof(ImagePath), typeof(string), typeof(TargetFaceCard), new PropertyMetadata(""));

        public static readonly DependencyProperty RemoveCommandProperty =
            DependencyProperty.Register(nameof(RemoveCommand), typeof(ICommand), typeof(TargetFaceCard), new PropertyMetadata(null));

        public string PersonName
        {
            get => (string)GetValue(PersonNameProperty);
            set => SetValue(PersonNameProperty, value);
        }

        public string ImagePath
        {
            get => (string)GetValue(ImagePathProperty);
            set => SetValue(ImagePathProperty, value);
        }

        public ICommand? RemoveCommand
        {
            get => (ICommand?)GetValue(RemoveCommandProperty);
            set => SetValue(RemoveCommandProperty, value);
        }

        public TargetFaceCard()
        {
            InitializeComponent();
        }

        private void OnRemoveClick(object sender, RoutedEventArgs e)
        {
            var item = DataContext as TargetFaceItem;
            if (RemoveCommand != null)
            {
                if (RemoveCommand.CanExecute(item))
                {
                    RemoveCommand.Execute(item);
                }
                else if (RemoveCommand.CanExecute(this))
                {
                    RemoveCommand.Execute(this);
                }
            }
        }
    }
}